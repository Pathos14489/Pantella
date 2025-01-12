from src.logging import logging
logging.info("Importing GPT-SoVITS.py...")
import src.tts_types.base_tts as base_tts
try:
    logging.info("Trying to import GPT-SoVITS libraries...")
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import numpy as np
    from transformers import (
        Wav2Vec2FeatureExtractor,
        HubertModel,
        AutoModelForMaskedLM,
        AutoTokenizer
    )
    import LangSegment
    import librosa
    from huggingface_hub import hf_hub_download
    from libraries.gpt_sovits.module.models import SynthesizerTrn
    from libraries.gpt_sovits.AR.models.t2s_lightning_module import Text2SemanticLightningModule
    from libraries.gpt_sovits.text import cleaned_text_to_sequence
    from libraries.gpt_sovits.text.cleaner import clean_text
    from libraries.gpt_sovits.module.mel_processing import spectrogram_torch
    from libraries.gpt_sovits.tools.my_utils import load_audio
    from libraries.gpt_sovits.feature_extractor.cnhubert import CNHubert
    logging.info("Imported GPT-SoVITS libraries")
except Exception as e:
    logging.error(f"Failed to import GPT-SoVITS: {e}")
    raise e
import random
import os
import json
import time
import tempfile
import traceback
import re
import chinese

import soundfile as sf
import torchaudio
from cached_path import cached_path


def process_text(texts):
    _text=[]
    if all(text in [None, " ", "\n",""] for text in texts):
        raise ValueError("Please enter valid text.")
    for text in texts:
        if text in  [None, " ", ""]:
            pass
        else:
            _text.append(text)
    return _text


def merge_short_text_in_array(texts, threshold):
    if (len(texts)) < 2:
        return texts
    result = []
    text = ""
    for ele in texts:
        text += ele
        if len(text) >= threshold:
            result.append(text)
            text = ""
    if (len(text) > 0):
        if len(result) == 0:
            result.append(text)
        else:
            result[len(result) - 1] += text
    return result

def clean_text_inf(text, language, version):
    phones, word2ph, norm_text = clean_text(text, language, version)
    phones = cleaned_text_to_sequence(phones, version)
    return phones, word2ph, norm_text


# def load_custom(ckpt_path: str, vocab_path="", model_cfg=None):
#     ckpt_path, vocab_path = ckpt_path.strip(), vocab_path.strip()
#     if ckpt_path.startswith("hf://"):
#         ckpt_path = str(cached_path(ckpt_path))
#     if vocab_path.startswith("hf://"):
#         vocab_path = str(cached_path(vocab_path))
#     if model_cfg is None:
#         model_cfg = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
#     return load_model(DiT, model_cfg, ckpt_path, vocab_file=vocab_path)
class DictToAttrRecursive(dict):
    def __init__(self, input_dict):
        super().__init__(input_dict)
        for key, value in input_dict.items():
            if isinstance(value, dict):
                value = DictToAttrRecursive(value)
            self[key] = value
            setattr(self, key, value)

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(f"Attribute {item} not found")

    def __setattr__(self, key, value):
        if isinstance(value, dict):
            value = DictToAttrRecursive(value)
        super(DictToAttrRecursive, self).__setitem__(key, value)
        super().__setattr__(key, value)

    def __delattr__(self, item):
        try:
            del self[item]
        except KeyError:
            raise AttributeError(f"Attribute {item} not found")

dict_language_v1 = {
    "Chinese": "all_zh",#全部按Chinese识别
    "English": "en",#全部按English识别#######不变
    "Japanese": "all_ja",#全部按Japanese识别
    "Chinese-English Mixed": "zh",#按Chinese-English Mixed识别####不变
    "Japanese-English Mixed": "ja",#按Japanese-English Mixed识别####不变
    "Multilingual Mixed": "auto",#多语种启动切分识别语种
}
dict_language_v2 = {
    "Chinese": "all_zh",#全部按Chinese识别
    "English": "en",#全部按English识别#######不变
    "Japanese": "all_ja",#全部按Japanese识别
    "Yue": "all_yue",#全部按Chinese识别
    "Korean": "all_ko",#全部按Korean识别
    "Chinese-English Mixed": "zh",#按Chinese-English Mixed识别####不变
    "Japanese-English Mixed": "ja",#按Japanese-English Mixed识别####不变
    "Yue-English Mixed": "yue",#按Yue-English Mixed识别####不变
    "Korean-English Mixed": "ko",#按Korean-English Mixed识别####不变
    "Multilingual Mixed": "auto",#多语种启动切分识别语种
    "Multilingual Mixed(Yue)": "auto_yue",#多语种启动切分识别语种
}

splits = {"，", "。", "？", "！", ",", ".", "?", "!", "~", ":", "：", "—", "…", }
punctuation = set(['!', '?', '…', ',', '.', '-'," "])

def split(todo_text):
    todo_text = todo_text.replace("……", "。").replace("——", "，")
    if todo_text[-1] not in splits:
        todo_text += "。"
    i_split_head = i_split_tail = 0
    len_text = len(todo_text)
    todo_texts = []
    while 1:
        if i_split_head >= len_text:
            break  # 结尾一定有标点，所以直接跳出即可，最后一段在上次已加入
        if todo_text[i_split_head] in splits:
            i_split_head += 1
            todo_texts.append(todo_text[i_split_tail:i_split_head])
            i_split_tail = i_split_head
        else:
            i_split_head += 1
    return todo_texts


def cut1(inp):
    inp = inp.strip("\n")
    inps = split(inp)
    split_idx = list(range(0, len(inps), 4))
    split_idx[-1] = None
    if len(split_idx) > 1:
        opts = []
        for idx in range(len(split_idx) - 1):
            opts.append("".join(inps[split_idx[idx]: split_idx[idx + 1]]))
    else:
        opts = [inp]
    opts = [item for item in opts if not set(item).issubset(punctuation)]
    return "\n".join(opts)

def cut2(inp):
    inp = inp.strip("\n")
    inps = split(inp)
    if len(inps) < 2:
        return inp
    opts = []
    summ = 0
    tmp_str = ""
    for i in range(len(inps)):
        summ += len(inps[i])
        tmp_str += inps[i]
        if summ > 50:
            summ = 0
            opts.append(tmp_str)
            tmp_str = ""
    if tmp_str != "":
        opts.append(tmp_str)
    # print(opts)
    if len(opts) > 1 and len(opts[-1]) < 50:  ##如果最后一个太短了，和前一个合一起
        opts[-2] = opts[-2] + opts[-1]
        opts = opts[:-1]
    opts = [item for item in opts if not set(item).issubset(punctuation)]
    return "\n".join(opts)

def cut3(inp):
    inp = inp.strip("\n")
    opts = ["%s" % item for item in inp.strip("。").split("。")]
    opts = [item for item in opts if not set(item).issubset(punctuation)]
    return  "\n".join(opts)

def cut4(inp):
    inp = inp.strip("\n")
    opts = ["%s" % item for item in inp.strip(".").split(".")]
    opts = [item for item in opts if not set(item).issubset(punctuation)]
    return "\n".join(opts)

# contributed by https://github.com/AI-Hobbyist/GPT-SoVITS/blob/main/GPT_SoVITS/inference_webui.py
def cut5(inp):
    inp = inp.strip("\n")
    punds = {',', '.', ';', '?', '!', '、', '，', '。', '？', '！', ';', '：', '…'}
    mergeitems = []
    items = []

    for i, char in enumerate(inp):
        if char in punds:
            if char == '.' and i > 0 and i < len(inp) - 1 and inp[i - 1].isdigit() and inp[i + 1].isdigit():
                items.append(char)
            else:
                items.append(char)
                mergeitems.append("".join(items))
                items = []
        else:
            items.append(char)

    if items:
        mergeitems.append("".join(items))

    opt = [item for item in mergeitems if not set(item).issubset(punds)]
    return "\n".join(opt)

logging.info("Imported required libraries in GPT-SoVITS.py")

tts_slug = "GPT-SoVITS"
class Synthesizer(base_tts.base_Synthesizer):
    def __init__(self, conversation_manager, ttses = []):
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        logging.info(f"Initializing {self.tts_slug}...")
        self.torch_dtype=torch.float16 if self.config.gpt_sovits_is_half == True else torch.float32
        self.np_dtype=np.float16 if self.config.gpt_sovits_is_half == True else np.float32
        

        # bert_path = ".\\data\\models\\gpt_sovits\\chinese-roberta-wwm-ext-large\\"
        # bert_path = os.path.abspath(bert_path)
        self.tokenizer = AutoTokenizer.from_pretrained("hfl/chinese-roberta-wwm-ext-large")
        self.bert_model = AutoModelForMaskedLM.from_pretrained("hfl/chinese-roberta-wwm-ext-large")
        if self.config.gpt_sovits_is_half == True:
            self.bert_model = self.bert_model.half()
        self.bert_model = self.bert_model.to(self.config.gpt_sovits_device)
        
        downloaded = False
        
        sovits_base_dir_path = ".\\data\\models\\gpt_sovits\\"
        sovits_base_dir_path = os.path.abspath(sovits_base_dir_path) + "\\"
        os.makedirs(sovits_base_dir_path, exist_ok=True)
        if not os.path.exists(sovits_base_dir_path+"s2G488k.pth"):
            logging.info("Downloading s2G488k.pth")
            hf_hub_download("lj1995/GPT-SoVITS", "s2G488k.pth", local_dir=sovits_base_dir_path)
            downloaded = True
        if not os.path.exists(sovits_base_dir_path+"s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt"):
            logging.info("Downloading s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt")
            hf_hub_download("lj1995/GPT-SoVITS", "s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt", local_dir=sovits_base_dir_path)
            downloaded = True
        if not os.path.exists(sovits_base_dir_path+"s2D488k.pth"):
            logging.info("Downloading s2D488k.pth")
            hf_hub_download("lj1995/GPT-SoVITS", "s2D488k.pth", local_dir=sovits_base_dir_path)
            downloaded = True

        cnhubert_base_dir_path = sovits_base_dir_path+"chinese-hubert-base\\"
        os.makedirs(cnhubert_base_dir_path, exist_ok=True)
        if not os.path.exists(cnhubert_base_dir_path+"pytorch_model.bin"):
            logging.info("Downloading chinese-hubert-base/pytorch_model.bin")
            hf_hub_download("lj1995/GPT-SoVITS", "chinese-hubert-base/pytorch_model.bin", local_dir=sovits_base_dir_path)
            downloaded = True
        if not os.path.exists(cnhubert_base_dir_path+"preprocessor_config.json"):
            logging.info("Downloading chinese-hubert-base/preprocessor_config.json")
            hf_hub_download("lj1995/GPT-SoVITS", "chinese-hubert-base/preprocessor_config.json", local_dir=sovits_base_dir_path)
            downloaded = True
        # if not os.path.exists(cnhubert_base_dir_path+"chinese-hubert-base_preprocessor_config.json"):
        #     logging.info("Downloading chinese-hubert-base/chinese-hubert-base_preprocessor_config.json")
        #     hf_hub_download("lj1995/GPT-SoVITS", "chinese-hubert-base/chinese-hubert-base_preprocessor_config.json", local_dir=cnhubert_base_dir_path)
        #     downloaded = True
        if not os.path.exists(cnhubert_base_dir_path+"chinese-hubert-base_config.json"):
            logging.info("Downloading chinese-hubert-base/chinese-hubert-base_config.json")
            hf_hub_download("lj1995/GPT-SoVITS", "chinese-hubert-base/config.json", local_dir=sovits_base_dir_path)
            downloaded = True

        if downloaded:
            logging.info("All models downloaded")

        self.ssl_model = CNHubert(cnhubert_base_dir_path)
        self.ssl_model.eval()
        if self.config.gpt_sovits_is_half == True:
            self.ssl_model = self.ssl_model.half().to(self.config.gpt_sovits_device)
        else:
            self.ssl_model = self.ssl_model.to(self.config.gpt_sovits_device)

        self.vq_model = None
        self.t2s_model = None
        self.hps = None
        self.hz = 50
        self.max_sec = 10
        self.cache = {}

        self.gpt_sovits_sovits_path = sovits_base_dir_path+"s2G488k.pth"
        self.gpt_sovits_gpt_path = sovits_base_dir_path+"s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt"

        self.change_gpt_weights()
        self.change_sovits_weights()

        logging.info(f'{self.tts_slug} speaker wavs folders: {self.speaker_wavs_folders}')
        logging.config(f'{self.tts_slug} - Available voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("GPT So Vits is ready to go.", random_voice)

    def voices(self):
        """Return a list of available voices"""
        voices = []
        for speaker_wavs_folder in self.speaker_wavs_folders:
            for speaker_wav_file in os.listdir(speaker_wavs_folder):
                speaker = speaker_wav_file.split(".")[0]
                if speaker_wav_file.endswith(".wav") and speaker not in voices:
                    voices.append(speaker)
        for banned_voice in self.config.gpt_sovits_banned_voice_models:
            if banned_voice in voices:
                voices.remove(banned_voice)
        return voices
    
    def voice_model_settings(self, voice_model):
        # speaker voice model settings are stored in ./data/chat_tts_inference_settings/{tts_language_code}/{voice_model}.json
        settings = {
            "transcription": ""
        }
        if self.config.linux_mode:
            voice_model_settings_path = os.path.abspath(f"./data/GPT-SoVITS_inference_settings/{self.language['tts_language_code']}/{voice_model}.json")
        else:
            voice_model_settings_path = os.path.abspath(f".\\data\\GPT-SoVITS_inference_settings\\{self.language['tts_language_code']}\\{voice_model}.json")
        if os.path.exists(voice_model_settings_path):
            with open(voice_model_settings_path, "r") as f:
                voice_model_settings = json.load(f)
            for setting in settings:
                if setting in voice_model_settings:
                    settings[setting] = voice_model_settings[setting]
        return settings
    
    def get_speaker_wav_path(self, voice_model):
        """Get the path to the wav filepath to a voice sample for the specified voice model if it exists"""
        list_of_files = []
        for speaker_wavs_folder in self.speaker_wavs_folders:
            if os.path.exists(os.path.join(speaker_wavs_folder, f"{voice_model}")) and os.path.isdir(os.path.join(speaker_wavs_folder, f"{voice_model}")): # check if a folder exists at the path for the specified voice model's wavs
                list_of_files = os.listdir(os.path.join(speaker_wavs_folder, f"{voice_model}"))
                list_of_files = [os.path.join(speaker_wavs_folder, f"{voice_model}", file) for file in list_of_files]
        for speaker_wavs_folder in self.speaker_wavs_folders:
            if os.path.exists(os.path.join(speaker_wavs_folder, f"{voice_model}.wav")):
                speaker_wav_path = os.path.join(speaker_wavs_folder, f"{voice_model}.wav")
                return speaker_wav_path, list_of_files
        return None
    
    def get_spepc(self, filename):
        audio = load_audio(filename, int(self.hps.data.sampling_rate))
        audio = torch.FloatTensor(audio)
        maxx=audio.abs().max()
        if(maxx>1):audio/=min(2,maxx)
        audio_norm = audio
        audio_norm = audio_norm.unsqueeze(0)
        spec = spectrogram_torch(
            audio_norm,
            self.hps.data.filter_length,
            self.hps.data.sampling_rate,
            self.hps.data.hop_length,
            self.hps.data.win_length,
            center=False,
        )
        return spec

    def get_bert_feature(self, text, word2ph):
        with torch.no_grad():
            inputs = self.tokenizer(text, return_tensors="pt")
            for i in inputs:
                inputs[i] = inputs[i].to(self.config.gpt_sovits_device)
            res = self.bert_model(**inputs, output_hidden_states=True)
            res = torch.cat(res["hidden_states"][-3:-2], -1)[0].cpu()[1:-1]
        assert len(word2ph) == len(text)
        phone_level_feature = []
        for i in range(len(word2ph)):
            repeat_feature = res[i].repeat(word2ph[i], 1)
            phone_level_feature.append(repeat_feature)
        phone_level_feature = torch.cat(phone_level_feature, dim=0)
        return phone_level_feature.T

    def get_phones_and_bert(self, text, final=False):
        language = self.config.gpt_sovits_prompt_language
        version = self.config.gpt_sovits_version
        if language in {"en", "all_zh", "all_ja", "all_ko", "all_yue"}:
            language = language.replace("all_","")
            if language == "en":
                LangSegment.setfilters(["en"])
                formattext = " ".join(tmp["text"] for tmp in LangSegment.getTexts(text))
            else:
                # 因无法区别中日Korean汉字,以用户输入为准
                formattext = text
            while "  " in formattext:
                formattext = formattext.replace("  ", " ")
            if language == "zh":
                if re.search(r'[A-Za-z]', formattext):
                    formattext = re.sub(r'[a-z]', lambda x: x.group(0).upper(), formattext)
                    formattext = chinese.mix_text_normalize(formattext)
                    return self.get_phones_and_bert(formattext, "zh" ,version)
                else:
                    phones, word2ph, norm_text = clean_text_inf(formattext, language, version)
                    bert = self.get_bert_feature(norm_text, word2ph).to(self.config.gpt_sovits_device)
            elif language == "yue" and re.search(r'[A-Za-z]', formattext):
                    formattext = re.sub(r'[a-z]', lambda x: x.group(0).upper(), formattext)
                    formattext = chinese.mix_text_normalize(formattext)
                    return self.get_phones_and_bert(formattext,"yue",version)
            else:
                phones, word2ph, norm_text = clean_text_inf(formattext, language, version)
                bert = torch.zeros(
                    (1024, len(phones)),
                    dtype=self.torch_dtype
                ).to(self.config.gpt_sovits_device)
        elif language in {"zh", "ja", "ko", "yue", "auto", "auto_yue"}:
            textlist=[]
            langlist=[]
            LangSegment.setfilters(["zh","ja","en","ko"])
            if language == "auto":
                for tmp in LangSegment.getTexts(text):
                    langlist.append(tmp["lang"])
                    textlist.append(tmp["text"])
            elif language == "auto_yue":
                for tmp in LangSegment.getTexts(text):
                    if tmp["lang"] == "zh":
                        tmp["lang"] = "yue"
                    langlist.append(tmp["lang"])
                    textlist.append(tmp["text"])
            else:
                for tmp in LangSegment.getTexts(text):
                    if tmp["lang"] == "en":
                        langlist.append(tmp["lang"])
                    else:
                        # 因无法区别中日Korean汉字,以用户输入为准
                        langlist.append(language)
                    textlist.append(tmp["text"])
            print(textlist)
            print(langlist)
            phones_list = []
            bert_list = []
            norm_text_list = []
            for i in range(len(textlist)):
                lang = langlist[i]
                phones, word2ph, norm_text = clean_text_inf(textlist[i], lang, version)
                bert = self.get_bert_inf(phones, word2ph, norm_text, lang)
                phones_list.append(phones)
                norm_text_list.append(norm_text)
                bert_list.append(bert)
            bert = torch.cat(bert_list, dim=1)
            phones = sum(phones_list, [])
            norm_text = ''.join(norm_text_list)

        if not final and len(phones) < 6:
            return self.get_phones_and_bert("." + text,final=True)

        return phones, bert.to(self.torch_dtype), norm_text

    @property
    def dict_language(self):
        return dict_language_v1 if self.config.gpt_sovits_version =='v1' else dict_language_v2

    def change_sovits_weights(self):
        dict_s2 = torch.load(self.gpt_sovits_sovits_path, map_location="cpu")
        self.hps = dict_s2["config"]
        self.hps = DictToAttrRecursive(self.hps)
        self.hps.model.semantic_frame_rate = "25hz"
        if dict_s2['weight']['enc_p.text_embedding.weight'].shape[0] == 322:
            self.hps.model.version = "v1"
        else:
            self.hps.model.version = "v2"
        version = self.hps.model.version
        # print("sovitsVersion:",hps.model.version)
        self.vq_model = SynthesizerTrn(
            self.hps.data.filter_length // 2 + 1,
            self.hps.train.segment_size // self.hps.data.hop_length,
            n_speakers=self.hps.data.n_speakers,
            **self.hps.model
        )
        if ("pretrained" not in self.gpt_sovits_sovits_path):
            del self.vq_model.enc_q
        if self.config.gpt_sovits_is_half == True:
            self.vq_model = self.vq_model.half().to(self.config.gpt_sovits_device)
        else:
            self.vq_model = self.vq_model.to(self.config.gpt_sovits_device)
        self.vq_model.eval()
        print(self.vq_model.load_state_dict(dict_s2["weight"], strict=False))
        # with open("./weight.json")as f:
        #     data=f.read()
        #     data=json.loads(data)
        #     data["SoVITS"][version]=self.gpt_sovits_sovits_path
        # with open("./weight.json","w")as f:
        #     f.write(json.dumps(data))
        if self.config.gpt_sovits_prompt_language is not None and self.config.gpt_sovits_text_language is not None:
            if self.config.gpt_sovits_prompt_language in list(self.dict_language.keys()):
                prompt_text_update, prompt_language_update = {'__type__':'update'},  {'__type__':'update', 'value':self.config.gpt_sovits_prompt_language}
            else:
                prompt_text_update = {'__type__':'update', 'value':''}
                prompt_language_update = {'__type__':'update', 'value':"Chinese"}
            if self.config.gpt_sovits_text_language in list(self.dict_language.keys()):
                text_update, text_language_update = {'__type__':'update'}, {'__type__':'update', 'value':self.config.gpt_sovits_text_language}
            else:
                text_update = {'__type__':'update', 'value':''}
                text_language_update = {'__type__':'update', 'value':"Chinese"}
            return  {'__type__':'update', 'choices':list(self.dict_language.keys())}, {'__type__':'update', 'choices':list(self.dict_language.keys())}, prompt_text_update, prompt_language_update, text_update, text_language_update
     
    def change_gpt_weights(self):        
        dict_s1 = torch.load(self.gpt_sovits_gpt_path, map_location="cpu")
        config = dict_s1["config"]
        self.max_sec = config["data"]["max_sec"]
        self.t2s_model = Text2SemanticLightningModule(config, "****", is_train=False)
        self.t2s_model.load_state_dict(dict_s1["weight"])
        if self.config.gpt_sovits_is_half == True:
            self.t2s_model = self.t2s_model.half()
        self.t2s_model = self.t2s_model.to(self.config.gpt_sovits_device)
        self.t2s_model.eval()
        total = sum([param.nelement() for param in self.t2s_model.parameters()])
        print("Number of parameter: %.2fM" % (total / 1e6))
        # with open("./weight.json")as f:
        #     data=f.read()
        #     data=json.loads(data)
        #     data["GPT"][self.config.gpt_sovits_version]=self.gpt_sovits_gpt_path
        # with open("./weight.json","w")as f:
        #     f.write(json.dumps(data))

    def get_tts_wav(self, ref_wav_path, prompt_text, text, ref_free=False, speed=1, if_freeze=False, inp_refs=None):
        # if ref_wav_path:
        #     pass
        # else:
        #     gr.Warning('Please Upload the Reference Audio')
        # if text:
        #     pass
        # else:
        #     gr.Warning('Please Fill in the Terget Text')
        t = []
        if prompt_text is None or len(prompt_text) == 0:
            ref_free = True
        t0 = time.time()

        if not ref_free:
            prompt_text = prompt_text.strip("\n")
            if (prompt_text[-1] not in splits): prompt_text += "。" if self.config.gpt_sovits_prompt_language != "en" else "."
            print("Actual Input Reference Text:", prompt_text)
        text = text.strip("\n")
        # if (text[0] not in splits and len(get_first(text)) < 4): text = "。" + text if text_language != "en" else "." + text
        
        print("Actual Input Target Text:", text)
        zero_wav = np.zeros(
            int(self.hps.data.sampling_rate * 0.3),
            dtype=self.np_dtype
        )
        if not ref_free:
            with torch.no_grad():
                wav16k, sr = librosa.load(ref_wav_path, sr=16000)
                if (wav16k.shape[0] > 160000 or wav16k.shape[0] < 48000):
                    if self.config.gpt_sovits_error_on_too_short_or_too_long_audio:
                        # gr.Warning("Reference audio is outside the 3-10 second range, please choose another one!"))
                        raise OSError("Reference audio is outside the 3-10 second range, please choose another one! - You can disable this error in the settings, but I'm not sure how well it will work? Haven't really tested it besides turning it off on one voice that was causing me issues and it seemed fine?")
                    else:
                        logging.warning("Reference audio is outside the 3-10 second range, please choose another one! - You can toggle this to error out in the settings if too long/too short voices are causing any issues for you.")
                wav16k = torch.from_numpy(wav16k)
                zero_wav_torch = torch.from_numpy(zero_wav)
                if self.config.gpt_sovits_is_half == True:
                    wav16k = wav16k.half().to(self.config.gpt_sovits_device)
                    zero_wav_torch = zero_wav_torch.half().to(self.config.gpt_sovits_device)
                else:
                    wav16k = wav16k.to(self.config.gpt_sovits_device)
                    zero_wav_torch = zero_wav_torch.to(self.config.gpt_sovits_device)
                wav16k = torch.cat([wav16k, zero_wav_torch])
                ssl_content = self.ssl_model.model(wav16k.unsqueeze(0))[
                    "last_hidden_state"
                ].transpose(
                    1, 2
                )  # .float()
                codes = self.vq_model.extract_latent(ssl_content)
                prompt_semantic = codes[0, 0]
                prompt = prompt_semantic.unsqueeze(0).to(self.config.gpt_sovits_device)

        t1 = time.time()
        t.append(t1-t0)

        if (self.config.gpt_sovits_cut_type == "every_4_seconds"):
            text = cut1(text)
        elif (self.config.gpt_sovits_cut_type == "per_50_chars"):
            text = cut2(text)
        # elif (self.config.gpt_sovits_cut_type == "按Chinese句号。切"):
        #     text = cut3(text)
        elif (self.config.gpt_sovits_cut_type == "punct"):
            text = cut4(text)
        # elif (self.config.gpt_sovits_cut_type == "Slice by every punct"):
        #     text = cut5(text)
        while "\n\n" in text:
            text = text.replace("\n\n", "\n")
        print("Actual Input Target Text (after sentence segmentation):", text)
        texts = text.split("\n")
        texts = process_text(texts)
        texts = merge_short_text_in_array(texts, 5)
        audio_opt = []
        if not ref_free:
            phones1, bert1, norm_text1 = self.get_phones_and_bert(prompt_text)

        for i_text,text in enumerate(texts):
            # 解决输入目标文本的空行导致报错的问题
            if (len(text.strip()) == 0):
                continue
            if (text[-1] not in splits): text += "。" if self.config.gpt_sovits_text_language != "en" else "."
            print("Actual Input Target Text (per sentence):", text)
            phones2, bert2, norm_text2 = self.get_phones_and_bert(text)
            print("Processed text from the frontend (per sentence):", norm_text2)
            if not ref_free:
                bert = torch.cat([bert1, bert2], 1)
                all_phoneme_ids = torch.LongTensor(phones1+phones2).to(self.config.gpt_sovits_device).unsqueeze(0)
            else:
                bert = bert2
                all_phoneme_ids = torch.LongTensor(phones2).to(self.config.gpt_sovits_device).unsqueeze(0)

            bert = bert.to(self.config.gpt_sovits_device).unsqueeze(0)
            all_phoneme_len = torch.tensor([all_phoneme_ids.shape[-1]]).to(self.config.gpt_sovits_device)

            t2 = time.time()
            
            if(i_text in self.cache and if_freeze==True):pred_semantic=self.cache[i_text]
            else:
                with torch.no_grad():
                    pred_semantic, idx = self.t2s_model.model.infer_panel(
                        all_phoneme_ids,
                        all_phoneme_len,
                        None if ref_free else prompt,
                        bert,
                        # prompt_phone_len=ph_offset,
                        top_k=self.config.gpt_sovits_top_k,
                        top_p=self.config.gpt_sovits_top_p,
                        temperature=self.config.gpt_sovits_temperature,
                        early_stop_num=self.hz * self.max_sec,
                    )
                    pred_semantic = pred_semantic[:, -idx:].unsqueeze(0)
                    self.cache[i_text]=pred_semantic
            t3 = time.time()
            refers=[]
            if(inp_refs):
                for path in inp_refs:
                    try:
                        refer = self.get_spepc(path).to(self.torch_dtype).to(self.config.gpt_sovits_device)
                        refers.append(refer)
                    except:
                        traceback.print_exc()
            if(len(refers)==0):
                refers = [self.get_spepc(ref_wav_path).to(self.torch_dtype).to(self.config.gpt_sovits_device)]
            audio = (self.vq_model.decode(pred_semantic, torch.LongTensor(phones2).to(self.config.gpt_sovits_device).unsqueeze(0), refers,speed=speed).detach().cpu().numpy()[0, 0])
            max_audio=np.abs(audio).max()#简单防止16bit爆音
            if max_audio>1:audio/=max_audio
            audio_opt.append(audio)
            audio_opt.append(zero_wav)
            t4 = time.time()
            t.extend([t2 - t1,t3 - t2, t4 - t3])
            t1 = time.time()
        print("%.3f\t%.3f\t%.3f\t%.3f" % (t[0], sum(t[1::3]), sum(t[2::3]), sum(t[3::3]))
        )
        yield self.hps.data.sampling_rate, (np.concatenate(audio_opt, 0) * 32768).astype(
            np.int16
        )

    def _synthesize(self, voiceline, voice_model, voiceline_location, aggro=0):
        """Synthesize the audio for the character specified using ParlerTTS"""
        logging.output(f'{self.tts_slug} - synthesizing {voiceline} with voice model "{voice_model}"...')
        speaker_wav_path, inp_refs = self.get_speaker_wav_path(voice_model)
        logging.output(speaker_wav_path, inp_refs)
        settings = self.voice_model_settings(voice_model)
        logging.output(f'{self.tts_slug} - using voice model settings: {settings}')
        if not voiceline.endswith(".") and not voiceline.endswith("!") and not voiceline.endswith("?"): # Add a period to the end of the voiceline if it doesn't have one.
            voiceline += "."

        # Synthesize audio
        synthesis_result = self.get_tts_wav(prompt_text=settings["transcription"],
            ref_wav_path=speaker_wav_path, 
            text=voiceline,
            inp_refs=inp_refs
        )
        
        result_list = list(synthesis_result)

        if result_list:
            last_sampling_rate, last_audio_data = result_list[-1]
            sf.write(voiceline_location, last_audio_data, last_sampling_rate)
            print(f"Audio saved to {voiceline_location}")
            logging.output(f'{self.tts_slug} - synthesized {voiceline} with voice model "{voice_model}"')