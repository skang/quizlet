import requests
from random import shuffle
import json
import os
import re
import sys
from quizlet_secret import QUIZLET_CLIENT_ID

###########################################################################
# Constants
###########################################################################
SET_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "sets")

###########################################################################
# Helper functions
###########################################################################
def get_answer_parts(termStr):
    answerPartList = filter(None, termStr.split("\n"))
    return answerPartList

def get_keyterms(answerPart):
    keyterms =  re.findall(r'\[[^]]+\]', answerPart)

    # get rid of surrounding brackets
    for i,keyterm in enumerate(keyterms):
        keyterms[i] = keyterm[1:-1]

    return keyterms

def user_answer_index(answer, parts):
    answer = answer.lower()
    for i, part in enumerate(parts):
        keyterms = get_keyterms(part)
        nonMatchedTerm = 0
        for keyterm in keyterms:
            keyterm = keyterm.lower()
            if answer.find(keyterm) == -1:
                nonMatchedTerm += 1
        if nonMatchedTerm == 0:
            return i
    return -1

def make_quizlet_request(endpoint):
    params = {"client_id": QUIZLET_CLIENT_ID, "whitespace": 0}
    apiPrefix = "https://api.quizlet.com/2.0"
    url = os.path.join(apiPrefix, endpoint)
    r = requests.get(url=url, params=params)
    dictFromJSON = json.loads(r.content)

    # Force status code key. Quizlet doesn't put one in for 200, only errors
    dictFromJSON['http_code'] = r.status_code
    return dictFromJSON

def get_flashcard_set(setID):
    return  make_quizlet_request("sets/%s" % setID)

def save_flashcard_set_terms_to_file(flashcardSet, f):
    termsJSON = json.dumps(flashcardSet['terms'])
    f.write(termsJSON)

def load_flashcard_set_terms_from_file(f):
    termJSON = f.read()
    return json.loads(termJSON)

def check_answer(userAnswer, answerParts):
    '''
    If userAnswer is in the answerParts list, remove it from the list and
    return True. Otherwise return False
    '''
    answerIndex = user_answer_index(userAnswer, answerParts)
    if answerIndex != -1:
        answerParts.pop(answerIndex)
        return True
    else:
        return False

def hintify(answerPart):
    '''
    Return a string signifying a hint of an answerPart
    '''
    answerStr = list(answerPart)
    inBracket = False
    i = 0
    startOfNewWord = False
    while i < len(answerStr):
        if not inBracket and answerStr[i] != '[':
            i += 1
        elif not inBracket and answerStr[i] == '[':
            inBracket = True
            i += 2

        elif inBracket and answerStr[i] != ']':
            if answerStr[i] == " ":
                startOfNewWord = True
            else:
                if startOfNewWord:
                    startOfNewWord = False
                else:
                    answerStr[i] = "_"
            i += 1
        elif inBracket and answerStr[i] == ']':
            inBracket = False
            i += 1

    return "".join(answerStr)



######################################################
# Untested functions
######################################################

def download_flashcard_set(setID):
    flashcardSet = get_flashcard_set(setID)

    if (flashcardSet['http_code'] != 200):
        print("Unable to access flashcard set %s" % setID)
        return

    # Get computer friendly set name
    cardURL = flashcardSet['url'].split('/')[-2]
    setFilename = cardURL + ".quiz"
    setPath = os.path.join(SET_DIR, setFilename)

    f = open(setPath, 'w')
    save_flashcard_set_terms_to_file(flashcardSet, f)
    f.close()

    title = flashcardSet['title']
    print("Downloaded '%s' set to sets/%s" % (title, setFilename))

def quiz_from_file(setPath):
    f = open(setPath)
    try:
        terms = load_flashcard_set_terms_from_file(f)
    except Exception, e:
        print("Exception occured loading %s:\n%s" % (setPath, str(e)))

    if not len(terms):
        raise Exception("No terms found in set %s" % setPath)

    shuffle(terms)

    #############################################################
    # Helper function for displaying terms to the the quiz taker 
    #############################################################
    def display_intro():
        print("=" * 50)
        print("Quizlet Quizzer!")
        print("(Enter h as your answer for help and options)")
        print("=" * 50 + "\n")

    def display_term(term, answerParts):
        print("\n(%d parts remaining) %s " % (len(answerParts), term['term']))

    def display_help():
        print("\n=============================================================")
        print("Quiz help! Current options are\n") 
        print("h: This help screen")
        print("hint: Receive a hint")
        print("see: See an answer part. You will have to repeat the question")
        print("skip: Skip this question. \n")
        print("Everything else will be considered an answer to the question")
        print("=============================================================")

    def display_hint(answerParts):
        print(hintify(answerParts[0]))

    def see_answer_part(answerParts):
        print(answerParts[0])
        print("You will have to repeat this question later!")

    ###############################
    # Begin the quiz!
    ###############################
    display_intro()
    for questionNumber,term in enumerate(terms):
        answerParts = get_answer_parts(term['definition'])
        print("Question %d/%d" % (questionNumber+1, len(terms)))

        while answerParts:
            display_term(term, answerParts)
            userAnswer = raw_input('Your answer: ')
            print("")

            ##################
            # Command options
            ##################
            if userAnswer == "h":
                display_help()
            elif userAnswer == "hint":
                display_hint(answerParts)
            elif userAnswer == "see":
                see_answer_part(answerParts)
                # Force a repeat of this question later, but don't keep
                # appending the same question if the user wants to see more
                # answer parts.
                if(terms[-1] != term):
                    terms.append(term)
            elif userAnswer == "skip":
                break

            ###########################################
            # Check for correct answer if not an option
            ###########################################
            elif(check_answer(userAnswer, answerParts)):
                print("Correct!")
            else:
                print("Incorrect")

    print("Finished!")


######################################################
# Begin script execution
######################################################
if __name__ == "__main__":

    # I don't feel like dealing with argparse. Fork if you care enough :P
    if(len(sys.argv) < 2):
        print("\nFlashcard set id# or path to quizlet file required\n")
        exit()

    # If a file, start the quiz
    # If a set Id, get card information and save json to file.
    arg = sys.argv[1]   

    if(os.path.exists(arg)):
        quiz_from_file(arg)
    elif(arg.isdigit()):
        download_flashcard_set(arg)
    else:
        print("\nFlashcard set id# or path to quizlet file required\n")
    