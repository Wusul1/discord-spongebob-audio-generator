import discord
import json
import random
import os
import re
import requests
import uuid
import time
import string
import asyncio
from pydub import AudioSegment
import websockets
from websockets.sync.client import connect
from discord.ext import commands

intents = discord.Intents.all()
bot = discord.Client(intents=intents)

CHARMODELS = {
    "spongebob": "TM:4hy6m7f7zeny",
    "patrick": "TM:ptcaavcfhwxd",
    "sandy": "TM:eaachm5yecgz",
    "mr. krabs": "TM:ade4ta7rc720",
    "squidwart": "TM:4e2xqpwqaggr"
}

async def merge_wav_with_music(folder_path, music_file_path, output_file_path):
    music = AudioSegment.from_file(music_file_path)
    music = music+3
    music = music-20
    merged_audio = AudioSegment.silent(duration=0)
    num_files = 0
    for file in os.listdir(folder_path):
        num_files+=1
    for i in range(1,num_files+1):
        filename=str(i)+".wav"
        if filename.endswith(".wav"):
            file_path = os.path.join(folder_path, filename)
            audio = AudioSegment.from_file(file_path)
            merged_audio += audio + AudioSegment.silent(duration=1000)
    merged_audio = merged_audio.overlay(music)
    merged_audio.export(output_file_path, format="wav")
    
async def generate_speech(char, text_to_speak, charmodels):
    wav_storage_server = "https://storage.googleapis.com/vocodes-public"
    uu_id = uuid.uuid4()
    modelname = charmodels[char]
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


async def extract_dialogue(string):
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
async def generate_random_string():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(50))
async def charstring(chars):
    final = ""
    for char in chars:
        final+=" and "
        final+=char
    return final
async def dbrx(prompt):
    import requests
    import json

    response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers={
    "Authorization": "KEY",
    },
    data=json.dumps({
    "model": "nousresearch/nous-hermes-2-mixtral-8x7b-dpo", # Optional
    "messages": [
      {"role": "user", "content": prompt}
    ]
    })
    )  
    return json.loads(response.text)["choices"][0]["message"]["content"]
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.content.lower().startswith('spongebot:'):
        if "/" in message.content: 
           newchars = message.content.split("/")[1]
           drecks = message.content.split("/")[0]
        else:
           drecks = message.content
           
        if "/" in message.content:
           prompt = "Write a conversation between spongebob and patrick"+charstring(newchars.split(","))+". The topic is: "+" ".join(drecks.split(" ")[1:])
        else:
            prompt = "Write a conversation between spongebob and patrick. The topic is: "+" ".join(drecks.split(" ")[1:])
        await message.channel.send("Schreibe script...")
        response_unprc = await dbrx(prompt)
        print(response_unprc)
        response = await extract_dialogue(response_unprc)
        audio_temp_identifier = await generate_random_string()
        if not os.path.isdir("temp/"+audio_temp_identifier):
            os.mkdir("temp/"+audio_temp_identifier)
        i=0
        print(response)
        for char_text_pair in response:
            time.sleep(10)
            i+=1
            await message.channel.send("Audio-Datei "+str(i)+" wird generiert...")
            char = char_text_pair[0]
            text = char_text_pair[1]
            while True:
                try:
                    print("generting audio file")
                    audio_file = await generate_speech(char, text, CHARMODELS)
                    break
                except:
                    continue
            with open("temp/"+audio_temp_identifier+"/"+str(i)+".wav", "wb") as file:
                file.write(audio_file)
        await message.channel.send("Audio-Dateien werden kombiniert...")
        await merge_wav_with_music("temp/"+audio_temp_identifier, "closing.mp3", "temp/"+audio_temp_identifier+"/final.mp3")
        with open("temp/"+audio_temp_identifier+"/final.mp3", "rb") as f:
           audio_file = discord.File(f)
           await message.channel.send(file=audio_file)
bot.run("TOKEN")  # Replace with your own bot token
#add erzähler
