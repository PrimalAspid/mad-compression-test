import os #test
from openai import OpenAI
import pandas

#admin stuff
llm = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)

#getting the test dataset
#currently the gsm8k-reasoning dataset: https://huggingface.co/datasets/thesven/gsm8k-reasoning/viewer?views%5B%5D=train
test_data = pandas.read_csv("test_dataset.csv", usecols=["question","short_answer"]) 

#shortcut to prompt llm
def llm_prompt(prompt):
  response = llm.responses.create(
    model="gpt-3.5-turbo-0125",
    input=prompt
  )

  return response.output_text

#llm reasoning method coding:
def CoT(question):
  return llm_prompt("Lets think step-by-step; " + question)

def vanilla_MAD(question):
  conversation_history = ""
  initial_answer = llm_prompt(question)
  condensed_answer = llm_prompt("condense '"+ initial_answer + "' into 1 sentence or less.")

  debator_prompt = "The question is '" + question + "' and an answer is '" + condensed_answer + "'. You are a debator, debating whether this answer is correct or not."
  affirmative_prompt = " You are on the affermative side. Please express your viewpoints. "
  negative_prompt = " You are on the negative side. You disagree with the affirmative side's points. Provide your own answer, and argue why it is better."
  judge_prompt = "You are a moderator. There will be two debators involved in a debate competition. They will present their answers and discuss their perspectives on an answers to question '" + question + "', the affermative side is arguing for the answer '"+initial_answer+"'. Your job is to evaluate both side's answers and either say if the debate is inconclusive, or state clearly the answer that is clearly better than the other. If you choose the latter, leave your answer in the form '[Quick thoughts] therefore the answer is [answer]' The debate goes as follow: "
  out_of_time_judge_prompt = "You are a moderator. There will be two debators involved in a debate competition. They will present their answers and discuss their perspectives on an answers to question '" + question + "', the affermative side is arguing for the answer '"+initial_answer+"'. Your job is to evaluate both side's answers and state clearly the answer that is clearly better than the other. Please leave the final verdict in the form '[thoughts] therefore the answer is [answer]'. The debate goes as follow: "

  #actual debate.
  running = True
  round_number = 0
  #initally affermative states position
  conversation_history += "affirmative side: \n" + llm_prompt(debator_prompt + affirmative_prompt + "\n" + conversation_history) + "\n"

  while running:
    conversation_history += "negative side: \n" + llm_prompt(debator_prompt + negative_prompt + "\n" + conversation_history) + "\n"
    conversation_history += "affirmative side: \n" + llm_prompt(debator_prompt + affirmative_prompt + "\n" + conversation_history) + "\n"

    #judge:
    verdict = llm_prompt(judge_prompt + "\n" + conversation_history + "\n Verdict: ")
    
    #end conditions
    round_number += 1 #putting a max ammount of rounds, because of time and money limitations
    #so min 1 round has passed
    if round_number > 1 and llm_prompt("Return 'False' if the following statement says the debate is inconclusive, otherwise return 'True'. '" + verdict + "'") == "True": #I have to use this roundabout method because the Judge llm is stupid, and cannot return a true or false reliably
      running = False
    elif round_number > 7:
      running = False
      verdict = llm_prompt(out_of_time_judge_prompt + "\n" + conversation_history)


  return llm_prompt("extract the actual answer from this explanation of an answer. Give it in the form of a number: " + verdict)

#testing
question_count = 0 # total num questions answered - in case something unexpected happens, I still want % correct. Also used as index
correct_questions = 0 #runnning total of number of questions correctly answered

running = True
while running:
  try:
    #-----
    current_question = test_data["question"][question_count]
    current_answer = str(test_data["short_answer"][question_count])

    #!!!!!!!!!!!!! sub the below line for the function you want to test !!!!!!!!!!!!
    llm_answer = vanilla_MAD(current_question)

    #tests wether the the answer in dataset and answer given by llm are the same, using the model to evaluate.
    is_correct = llm_prompt("return 'True' if the first statement is contained anywhere within the second statement, 'False' if not: '" + current_answer + "' and '" + llm_answer + "'")
    if is_correct == "True":
      correct_questions += 1

    #breaks the code at 100, because communication with openai api is reallly slow, and it would take about 8 hours to finish the whole dataset
    if question_count >= 1000:
      running = False
    
    #----
    question_count += 1
     
    #just printing something to give me a progress bar
    print(f"{question_count} : {is_correct} : {correct_questions / question_count * 100} ")

    
  except: #breaks when there is an error(either eof, openai api running out of tokens, etc)
    running = False

#adjuct question_count to account for the last "question_count += 1"
question_count -= 1 

#prints the results
percent_correct = correct_questions / question_count * 100
print(f"number tested : {question_count}")
print(f"percentage correct : {percent_correct}")