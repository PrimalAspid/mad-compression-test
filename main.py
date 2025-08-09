import os #test
from openai import OpenAI
import pandas

api_key_file = open("api_key.txt")

#admin stuff
llm = OpenAI(
    # This is the default and can be omitted
    api_key= api_key_file.readline().strip()
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

def smart_llm_prompt(prompt):
  response = llm.responses.create(
    model="o4-mini-2025-04-16",
    input=prompt
  )

  return response.output_text

#llm reasoning method coding:
def CoT(question):
  return llm_prompt("Lets think step-by-step; " + question)

def vanilla_MAD(question):
  #second is an extra instruction for debators
  return MAD(question, "", "")

def compressed_MAD(question):
  #second is an extra instruction for debators
  return MAD(question, " You must present your arguments in the form: explanation of point, must be less than 10 tokens, evidence to support point, must be less than 20 tokens, explanation of how evidence supports points - must be less than 40 tokens"," You must make 2 arguments: 1 to rebut your opponents last argument, and another to strengthen your position. You must present your arguments in the form: explanation of point, must be less than 10 tokens, evidence to support point, must be less than 20 tokens, explanation of how evidence supports points - must be less than 40 tokens")

def MAD(question, initial_instruction, extra_instruction):
  global total_token_count
  global token_sample_size

  conversation_history = ""
  initial_answer = llm_prompt(question)
  condensed_answer = llm_prompt("condense '"+ initial_answer + "' into 1 sentence or less.")

  debator_prompt = "You are a debater. Hello and welcome to the debate competition. It’s not necessary to fully agree with each other’s perspectives, as our objective is to find the correct answer. The debate topic is stated as follows: The question is '" + question + "' and an answer is '" + condensed_answer + "' Is this answer correct?"
  affirmative_prompt = " You are on the affermative side. Please express your viewpoints. "
  negative_prompt = " You are on the negative side. You disagree with the affirmative side's points. Provide your own answer, and argue why it is better."
  judge_prompt = "A dabate has occured about whether the answer to the question '" + question + "' is '" + initial_answer + "'. You are to judge if the debate is conclusive, and there is an obvious answer, or if the debate is inconclusive. If there is a clear answer, please state it. The debate went as follows: "
  out_of_time_judge_prompt = "A dabate has occured about whether the answer to the question '" + question + "' is '" + initial_answer + "'. You are to judge the correct answer. Please state this answer clearly. The debate went as follows: "

  #actual debate.
  running = True
  round_number = 0

  #initial affirming side
  conversation_history += "affirmative side: \n" + llm_prompt(debator_prompt + affirmative_prompt + initial_instruction + "\n" + conversation_history) + "\n"
  while running:
    conversation_history += "negative side: \n" + llm_prompt(debator_prompt + negative_prompt + extra_instruction + "\n" + conversation_history) + "\n"
    conversation_history += "affirmative side: \n" + llm_prompt(debator_prompt + affirmative_prompt + extra_instruction + "\n" + conversation_history) + "\n"

    #judge:
    verdict = llm_prompt(judge_prompt + "\n" + conversation_history + "\n Verdict: ")
    
    #end conditions
    round_number += 1 #putting a max ammount of rounds, because of time and money limitations
    #so min 1 round has passed
    if round_number > 1 and smart_llm_prompt("Return False if the following statement implies the debate is inconclusive, otherwise return True. '" + verdict + "'") == "True": #I have to use this roundabout method because the Judge llm is stupid, and cannot return a true or false reliably
      running = False
    elif round_number > 7:
      running = False
      verdict = llm_prompt(out_of_time_judge_prompt + "\n" + conversation_history)

  #counting tokens
  try:
    total_token_count += int(smart_llm_prompt("count how many tokens are used in the following converation. give your answer as a number only. I like cheese = 3. I cook pizza = 3. Harry and john went to the shop = 7. " + conversation_history + " = "))
    token_sample_size += 1
  except:
    print("error counting tokens")

  return verdict

#testing
question_count = 0 # total num questions answered - in case something unexpected happens, I still want % correct. Also used as index
correct_questions = 0 #runnning total of number of questions correctly answered

total_token_count = 0 
token_sample_size = 0

running = True
while running:
  try:
    #-----
    current_question = test_data["question"][question_count]
    current_answer = str(test_data["short_answer"][question_count])

    #!!!!!!!!!!!!! sub the below line for the function you want to test !!!!!!!!!!!!
    llm_answer = compressed_MAD(current_question)

    #tests wether the the answer in dataset and answer given by llm are the same, using the model to evaluate.  
    is_correct = smart_llm_prompt("return True if the first statement is contained anywhere within the second statement, False if not: '" + current_answer + "' and '" + llm_answer + "'")
    if is_correct == "True":
      correct_questions += 1

    #breaks the code at 100, because communication with openai api is reallly slow, and it would take about 8 hours to finish the whole dataset
    if question_count >= 100:
      running = False
    
    #----
    question_count += 1
     
    #just printing something to give me a progress bar
    print(f"{question_count} : {is_correct} : {correct_questions / question_count * 100}")

    
  except: #breaks when there is an error(either eof, openai api running out of tokens, etc)
    running = False

#adjuct question_count to account for the last "question_count += 1"
question_count -= 1 

#prints the results
percent_correct = correct_questions / question_count * 100
print(f"number tested : {question_count}")
print(f"percentage correct : {percent_correct}")
print(f"avg number tokens : {total_token_count / token_sample_size}")