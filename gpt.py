import os
import json
import aiohttp
import asyncio

import colorama
from colorama import Fore, Back, Style

from dotenv import load_dotenv
load_dotenv()
import read_pdf
from openai import OpenAI

# Get OPENAI_API_KEY from environment variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def compare_documents(model, prompt, file1, doc_type1, file2, doc_type2):

    # Print all parameters
    print("Model: ", model)
    print("Prompt: ", prompt)
    print("File 1: ", file1.name)
    print("Document Type 1: ", doc_type1)
    print("File 2: ", file2.name)
    print("Document Type 2: ", doc_type2)

    # Read the first file
    file1_text = None
    with open(file1.name, "r") as f:

        # If file is a PDF, convert it to text
        if file1.name.endswith(".pdf"):
            file1_text = read_pdf.read_pdf(file1.name)
        elif file1.name.endswith(".txt"):
            file1_text = f.read()
        else:
            return "File 1 is not a PDF or TXT file"

    #  Read the second file
    file2_text = None
    with open(file2.name, "r") as f:

        # If file is a PDF, convert it to text
        if file2.name.endswith(".pdf"):
            file2_text = read_pdf.read_pdf(file2.name)
        elif file2.name.endswith(".txt"):
            file2_text = f.read()
        else:
            return "File 2 is not a PDF or TXT file"


    full_message_for_gpt = f"""----- {doc_type1.upper()} -----\n{file1_text}\n\n----- {doc_type2.upper()} -----\n{file2_text}\n\n\n{prompt}"""

    print(full_message_for_gpt)

    # Create a completion using GPT API
    completion = client.chat.completions.create(
        model=model,
        messages=[
            # {"role": "system", "content": "You are an assistant."},
            {"role": "user", "content": full_message_for_gpt}
        ]
    )

    return completion.choices[0].message.content

def count_conditions(file_input):
  """
  Counts the number of conditions within a document using the GPT API.

  Parameters:
  file_input (str): Filepath to the document.

  Returns:
  str: The number of conditions within the document.
  str: An error message if the file type is not supported.

  Notes:
  - Only PDF and TXT file types are supported. If the file is not one of these types, the function will return an error message.
  """
  file_text = None
  with open(file_input.name, "r") as f:

      # If file is a PDF, convert it to text
      if file_input.name.endswith(".pdf"):
          file_text = read_pdf.read_pdf(file_input.name)
      elif file_input.name.endswith(".txt"):
          file_text = f.read()
      else:
          return "File 1 is not a PDF or TXT file"
      
  print(file_text)

  tools = [
    {
      "type": "function",
      "function": {
        "name": "count_conditions",
        "description": "Count the number of conditions in the document.",
        "parameters": {
          "type": "object",
          "properties": {
              "count": {
                "type": "integer",
                "description": "The number of conditions in the document."
              },
          },
          "required": ["count"],
        },
      }
    }
  ]
  messages = [{"role": "user", "content": f"Here is a document with conditions:\n\n{file_text}"}]
  completion = client.chat.completions.create(
    model="gpt-4o-2024-05-13",
    messages=messages,
    tools=tools,
    tool_choice={"type": "function", "function": {"name": "count_conditions"}}
  )

  count_json = json.loads(completion.choices[0].message.tool_calls[0].function.arguments)
  count = count_json["count"]

  return(count)

class FinishReasonError(Exception):
    pass

class LengthFinishReasonError(FinishReasonError):
    pass

def extract_info(file_input, starting_condition_number, ending_condition_number):
      
  file_text = None
  with open(file_input.name, "r") as f:

      # If file is a PDF, convert it to text
      if file_input.name.endswith(".pdf"):
          file_text = read_pdf.read_pdf(file_input.name)
      elif file_input.name.endswith(".txt"):
          file_text = f.read()
      else:
          return "File 1 is not a PDF or TXT file"

  conditions_list_description = f"Conditions {starting_condition_number} (inclusive) up to and including {ending_condition_number} extracted from the document. ALWAYS include the condition name."

  if starting_condition_number == ending_condition_number:
    print(f"Extracting condition {starting_condition_number} from the document.")
    conditions_list_description = f"Only condition {starting_condition_number} extracted from the document. ALWAYS includes the condition name."



  tools = [
    {
      "type": "function",
      "function": {
        "name": "format_info",
        "description": "Format the information extracted from the document.",
        "parameters": {
          "type": "object",
          "properties": {
              "conditions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "condition_name": {"type": "string", "description": "The name of the condition. REQUIRED."},
                        "condition_number": {"type": "integer", "description": "The number associated with the condition."},
                        "condition_text": {"type": "string", "description": "The text of the condition. Fix spacing issues. Include the same newlines as in the document."},
                    },
                },
                "description": conditions_list_description,
              },
          },
          "required": ["conditions", "conditions.condition_name"],
        },
      }
    }
  ]
  messages = [{"role": "user", "content": f"Here is a document with conditions:\n\n{file_text}\n\nExtract conditions {starting_condition_number} to {ending_condition_number}."}]

  json_object = {
      "custom_id": "request-1",
      "method": "POST",
      "url": "/v1/chat/completions",
      "body": {
          "model": "gpt-4o-2024-05-13",
          "messages": messages,
          "tools": tools,
          "tool_choice": {"type": "function", "function": {"name": "format_info"}}
      }
  }

  print("ADDING TO JSONL FILE")
  with open("test2.jsonl", "a") as jsonl_file:
      jsonl_file.write(json.dumps(json_object) + "\n")
  
  # return completion, completion.choices[0].message.tool_calls[0].function.arguments


  return None, "Failed to extract the correct number of conditions after multiple attempts"


def extract_info_chunked(file_input, number_of_conditions, chunk_size=5):
  """
  Extract information from a document in chunks, processing a specified number of conditions at a time.

  Parameters:
  file_input (str): Filepath to the document.
  number_of_conditions (int): The total number of conditions the document has.
  chunk_size (int, optional): The number of conditions to extract in each chunk. Default is 5.

  Returns:
  list of str: A list of condition chunks in JSON format.
  """

  chunks = []

  for i in range(0, number_of_conditions, chunk_size):
    end = min(i + chunk_size, number_of_conditions)


    print(Fore.YELLOW + "\nExtracting conditions", i + 1, "to", end, f"(of {number_of_conditions})\n" + Fore.RESET)
    chunk_completion, chunk = extract_info(file_input, i + 1, end)
    print(Fore.GREEN + chunk + Fore.RESET)
    chunks.append(chunk) 

  return chunks

def merge_json_chunks(chunks):

  merged = {
    "conditions": []
  }

  for chunk in chunks:
    chunk_json = json.loads(chunk)
    merged["conditions"].extend(chunk_json["conditions"])

  return json.dumps(merged) 


def extract_all_conditions(file_input, number_of_conditions, chunk_size=5):
  """
  Extract all conditions from a document by processing in chunks and merging the results.

  Parameters:
  file_input (str): Filepath to the document.
  number_of_conditions (int): The total number of conditions the document has.
  chunk_size (int, optional): The number of conditions to extract in each chunk. Default is 5.

  Returns:
  dict: A dictionary representing the merged JSON of all extracted conditions.
  """

  chunks = extract_info_chunked(file_input, number_of_conditions, chunk_size)
  merged = merge_json_chunks(chunks)

  # print the merged JSON, replacing \n with newlines by converting to a dictionary and then back to a string
  merged = json.loads(merged)

  print(Fore.CYAN + "\nMerged JSON:\n")
  print(merged)
  print(Fore.RESET)
  
  print(Fore.GREEN + "\nSuccessfully extracted all conditions!" + Fore.RESET)
  
  return merged


def extract_subcondition(condition_text):
    """
    Extract nested subconditions from a given condition text using the GPT API. E.g. a), i), 1), etc.

    Parameters:
    condition_text (str): The text of the condition to be broken down into subconditions.

    Returns:
    dict: A dictionary representing the formatted subconditions in JSON format.
    """

    tools = [
      {
        "type": "function",
        "function": {
          "name": "format_condition",
          "description": "Formats the input condition by breaking it down into nested subconditions",

          "parameters": {
            "type": "object",
            "properties": {

                  "clauses": {
                      "type": "array",
                      "items": {
                          "type": "object",
                          "properties": {
                              "subcondition_identifier": {"type": "string", "description": "The number, letter, or other identifier of the subcondition. E.g. 1), 1 a), i, etc. Write it exactly as it appears in the text (i.e. include brackets). If none, leave blank."},
                              "subcondition_text": {"type": "string", "description": "The text of the subcondition."},
                              "subconditions": {
                                  "type": "array",
                                  "items": {
                                      "type": "object",
                                      "properties": {
                                          "subcondition_identifier": {"type": "string", "description": "The number, letter, or other identifier of the subcondition. E.g. 1), 1 a), i, etc. Write it exactly as it appears in the text (i.e. include brackets)."},
                                          "subcondition_text": {"type": "string", "description": "The text of the subcondition."},
                                          "subconditions": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "subcondition_identifier": {"type": "string", "description": "The number, letter, or other identifier of the subcondition. E.g. 1), 1 a), i, etc. Write it exactly as it appears in the text (i.e. include brackets)."},
                                                    "subcondition_text": {"type": "string", "description": "The text of the subcondition."},
                                                    
                                                },
                                            },
                                        },
                                      },
                                  },
                              },
                          },
                      },
                  },

            },
            "required": ["clauses"],
          },

        }
      }
    ]
    messages = [{"role": "user", "content": f"Here is a condition:\n\n{condition_text}"}]
    completion = client.chat.completions.create(
      model="gpt-4o-2024-05-13",
      messages=messages,
      tools=tools,
      tool_choice={"type": "function", "function": {"name": "format_condition"}}

    )
  
    return completion.choices[0].message.tool_calls[0].function.arguments

def check_for_subconditions(input_condition_text):
  """
  Check if a given condition text contains subconditions using the GPT API. E.g. a), i), 1), etc.

  Parameters:
  input_condition_text (str): The text of the condition to be analyzed.

  Returns:
  bool: True if the condition contains subcondition identifiers, False otherwise.

  Notes:
  - Subcondition identifiers can be letters, numbers, bullet points, etc. New paragraphs or sentences are not considered subconditions.
  """
  tools = [
    {
      "type": "function",
      "function": {
        "name": "extract_subconditions",
        "description": "If the input condition contains subconditions, extract them.",

        "parameters": {
          "type": "object",
          "properties": {

            "contains_subcondition_identifiers": {
              "type": "boolean",
              "description": "Does the condition have subconditions? For example: a), 1., i., bullet points, etc. New paragraphs or sentences are not considered subconditions."
            },

          },
          "required": ["contains_subcondition_identifiers"],
        },

      }
    }
  ]
  messages = [{"role": "user", "content": f"Here is the text of a condition:\n\n{input_condition_text}"}]
  completion = client.chat.completions.create(
    model="gpt-4o-2024-05-13",
    messages=messages,
    tools=tools,
    tool_choice={"type": "function", "function": {"name": "extract_subconditions"}}
  )

  print(completion)

  result = json.loads(completion.choices[0].message.tool_calls[0].function.arguments)

  # If result is not null, return the value of contains_subconditions
  if result:
    return result["contains_subcondition_identifiers"]
  
  else:
     print(Fore.RED + "Error: result is null" + Fore.RESET)


def extract_all_subconditions(input_json):
  """
  Extract all subconditions for each condition in the provided JSON.

  Parameters:
  input_json (dict): A dictionary containing conditions with their texts.

  Returns:
  str: A JSON as a string with the updated conditions, including extracted subconditions.

  Notes:
  - This function iterates over each condition in the input JSON.
  - It checks if each condition has subconditions and extracts them if present.
  - If a condition does not have subconditions, it sets an empty array for "subconditions".
  """
  # For each condition, extract subconditions, then add them to the JSON
  for condition in input_json["conditions"]:

    # Check if the condition has subconditions
    print(Fore.CYAN + f"\nChecking for subconditions in condition {condition['condition_number']}:" + Fore.RESET)
    has_subconditions = check_for_subconditions(condition["condition_text"])

    if has_subconditions:
      print(Fore.GREEN + "This condition has subconditions!" + Fore.RESET)
    else:
      print(Fore.RED + "This condition does not have subconditions." + Fore.RESET)
      
      # Set subconditions to empty array
      condition["subconditions"] = []

      # Skip to next condition
      continue

    print(Fore.YELLOW + f"\nExtracting subconditions for condition {condition['condition_number']}:\n" + Fore.RESET)
    subcondition = extract_subcondition(condition["condition_text"])
    condition["subconditions"] = json.loads(subcondition)["clauses"]
    print(Fore.GREEN + subcondition + Fore.RESET)
    print(Fore.GREEN + f"Successfully extracted subconditions for condition {condition['condition_number']}!" + Fore.RESET)
    

  # Return new JSON with subconditions
  return json.dumps(input_json)
