import discord
import json
from discord.ext import commands
import random
import os
import re
import requests
import uuid
import time
import string
import json
from websockets.sync.client import connect
import asyncio

SPONGE_BOB_GENERATION_MAX_TRYS = 3

intents = discord.Intents.default()
intents.typing = False
intents.message_content = True
intents.presences = False

bot = commands.Bot(command_prefix='', intents=intents)
CHARMODELS = {
    "spongebob": "TM:4hy6m7f7zeny",
    "patrick": "TM:ptcaavcfhwxd",
    "sandy": "TM:eaachm5yecgz",
    "mr. krabs": "TM:ade4ta7rc720",
    "squidwart": "TM:4e2xqpwqaggr"
    }
from pydub import AudioSegment

def merge_wav_with_music(folder_path, music_file_path, output_file_path):
    # Load the music file
    music = AudioSegment.from_file(music_file_path)

    # Increase the volume of the music by 10%
    music = music + 3

    # Adjust the volume of the music by 60%
    music = music - 20

    # Initialize an empty audio segment to store the merged audio
    merged_audio = AudioSegment.silent(duration=0)

    # Iterate over the files in the folder
    num_files = 0
    for filename in os.listdir(folder_path):
        num_files+=1
    for i in range(1,num_files+1):
        filename=str(i)+".wav"
        if filename.endswith(".wav"):
            file_path = os.path.join(folder_path, filename)
            audio = AudioSegment.from_file(file_path)

            # Add the current audio segment and a 1-second pause to the merged audio
            merged_audio += audio + AudioSegment.silent(duration=1000)

    # Overlay the music onto the merged audio
    merged_audio = merged_audio.overlay(music)

    # Export the final merged audio to a file
    merged_audio.export(output_file_path, format="wav")
def generate_speech(char, text_to_speak):
    wav_storage_server = "https://storage.googleapis.com/vocodes-public"
    uu_id = uuid.uuid4()
    global CHARMODELS
    modelname = CHARMODELS[char]
    url = 'https://api.fakeyou.com/tts/inference'
    headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
    }
    data = {
    'uuid_idempotency_token': str(uu_id),
    'tts_model_token': modelname,
    'inference_text': text_to_speak
    }
    response = requests.post(url, headers=headers, json=data).text
    response = json.loads(response)
    token = response['inference_job_token']
    while True:
       time.sleep(1)
       url = 'https://api.fakeyou.com/tts/job/'+token
       headers = {'Accept': 'application/json'}
       response = requests.get(url, headers=headers).text
       response = json.loads(response)
       status = response['state']['status']
       print(status)
       if status == "complete_success":
           break
       if status == "attempt_failed":
           raise Exception("TTS Failed!")
    filepath = response['state']['maybe_public_bucket_wav_audio_path']
    return requests.get(wav_storage_server+filepath).content
def generate_random_string():
    characters = string.ascii_lowercase + string.digits
    random_string = ''.join(random.choices(characters, k=11))
    return random_string
def extract_dialogue(string):
    dialogue_list = []
    pattern = r"(\b[A-Z][a-zA-Z]+\b): (.+)"
    matches = re.findall(pattern, string)
    for match in matches:
        character = match[0].lower()
        dialogue = match[1]
        dialogue_list.append([character, dialogue])
    return dialogue_list

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    if not os.path.isdir("temp"):
        os.mkdir("temp")
        
def mosaicml_mpt_30b_chat_inference(prompt, shash):
    with connect("wss://mosaicml-mpt-30b-chat.hf.space/queue/join") as websocket:
        print("connected to ws")
        websocket.send('{"fn_index":1,"session_hash":"'+shash+'"}')
        while True:
            message = websocket.recv()
            if "send_data" in message:
                print("send_data")
                break
        websocket.send('{"data":["A conversation between a user and an LLM-based AI assistant. The assistant gives helpful and honest answers.",[["'+prompt+'",""]]],"event_data":null,"fn_index":3,"session_hash":"'+shash+'"}')
        print('{"data":["A conversation between a user and an LLM-based AI assistant. The assistant gives helpful and honest answers.",[["'+prompt+'",""]]],"event_data":null,"fn_index":3,"session_hash":"'+shash+'"}')
        while True:
            print("recv")
            message = websocket.recv()
            print(message)
            if "process_completed" in message:
                print("proc complete")
                break
        message = json.loads(message)
        print("done")
        return message['output']['data'][1][0][1]
    
def charstring(chars):
    final = ""
    for char in chars:
        final+=" and "
        final+=char
    return final
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.content.lower().startswith("chatmbt:"):
        await message.channel.send(mosaicml_mpt_30b_chat_inference(" ".join(message.content.split(" ")[1:])))
    if message.content.lower().startswith('spongebob:'):
        if "/" in message.content: 
           newchars = message.content.split("/")[1]
           drecks = message.content.split("/")[0]
        else:
           drecks = message.content
        if "/" in message.content:
           prompt = "Write a conversation between spongebob and patrick"+charstring(newchars.split(","))+". The topic is: "+" ".join(drecks.split(" ")[1:])+'. End your conversation with Patrick just saying "The End"'
        else:
            prompt = "Write a conversation between spongebob and patrick. The topic is: "+" ".join(drecks.split(" ")[1:])+'. End your conversation with Patrick just saying "The End"'
        responses = []
        max_parts = 5
        shash = generate_random_string()
        part = 1
        while True:
            if max_parts == 0:
                break
            print(f"part {part}")
            response_temp = mosaicml_mpt_30b_chat_inference(prompt, shash)
            responses+=response_temp
            part+=1
            if not "the end" in response_temp.lower():
                prompt="continue"
                max_parts-=1
                continue
            else:
                break
        print(responses)
        input("")
        response = extract_dialogue(response_temp)
        audio_temp_identifier = generate_random_string()
        if not os.path.isdir("temp/"+audio_temp_identifier):
            os.mkdir("temp/"+audio_temp_identifier)
        i=0
        for char_text_pair in response:
            time.sleep(10)
            i+=1
            char = char_text_pair[0]
            text = char_text_pair[1]
            audio_file = generate_speech(char, text)
            with open("temp/"+audio_temp_identifier+"/"+str(i)+".wav", "wb") as file:
                file.write(audio_file)
        merge_wav_with_music("temp/"+audio_temp_identifier, "closing.mp3", "temp/"+audio_temp_identifier+"/final.mp3")
        with open("temp/"+audio_temp_identifier+"/final.mp3", "rb") as f:
           audio_file = discord.File(f)
           await message.channel.send(file=audio_file)
bot.run("TOKEN")  # Replace with your own bot token

