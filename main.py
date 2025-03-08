import json
import aiohttp
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from astrbot.api.all import *
from astrbot.api.event import filter
@register("TTS_FREE", "达莉娅", "freetts", "1.0.0")
class ChatCollectorPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.tts_path = './data/plugins/ttsrooms.jsonl'
        # TTS配置
        self.model = '梅琳娜'
        self.ttsrooms = []
        self.flag2 = False
        self.flag = False
        if not os.path.exists(self.tts_path):
            self.save_ttsrooms()
            print(f"文件 {self.tts_path} 不存在，已创建并初始化。")
        else:
            print(f"文件 {self.tts_path} 已存在，跳过创建。")
        self.load_ttsrooms()
    '''TTS功能部分'''
    @filter.command("TTS")
    async def tts_switch(self, event: AstrMessageEvent):
        room = event.get_group_id()
        chain1 = [Plain(f"本群TTS启动（仅限本群）"), Face(id=337)]
        chain2 = [Plain(f"本群TTS关闭（仅限本群）"), Face(id=337)]
        if room in self.ttsrooms:
            self.ttsrooms.remove(room)
            self.save_ttsrooms()
            yield event.chain_result(chain2)
        else:
            self.ttsrooms.append(room)
            self.save_ttsrooms()
            yield event.chain_result(chain1)

    @filter.on_decorating_result(priority=100)
    async def voice(self, event: AstrMessageEvent):
        result = event.get_result()
        room = event.get_group_id()
        texts = result.get_plain_text()
        res = MessageChain()
        res.chain = result.chain
        adapter_name = event.get_platform_name()
        if room in self.ttsrooms:
            if adapter_name == "qq_official":
                logger.info("检测为官方机器人，自动忽略转语音请求")
                return
            if not result.chain:
                logger.info(f"返回消息为空,pass")
                return
            if not result.is_llm_result():
                logger.info(f"非LLM消息,pass")
                return
            if self.flag:
                await event.send(res)
            logger.info(f"LLM返回的文本是：{texts}")
            result.chain.remove(Plain(texts))

            text_chunks = [texts[i:i + 200] for i in range(0, len(texts), 200)]
            for chunk in text_chunks:
                det = await self.generate_voice(chunk, self.model)
                voice = MessageChain()
                voice.chain.append(Record.fromURL(det))
                await event.send(voice)

    @filter.command("切换音色")
    async def timbre_switch(self, event: AstrMessageEvent, model: str):
        # 允许切换的音色列表
        allowed_models = [
            "孙笑川", "东雪莲", "玛莲妮亚", "菈妮", "梅琳娜", "蒙葛特",
            "银手", "女v", "米莉森", "帕奇", "赛尔维斯", "丁真",
            "蔡徐坤", "科比", "富兰克林"
        ]
        # 验证 model 参数
        if model not in allowed_models:
            error_msg = f"请选择以下角色：{'、'.join(allowed_models)}"
            yield event.chain_result([Plain(error_msg), Face(id=174)])  # 174 是困惑表情
            return

        # 更新 model 并切换状态
        self.model = model
        response = [Plain(f"【{model}】音色已成功切换"), Face(id=337)]  # 337 是笑脸
        yield event.chain_result(response)

    @filter.command("filter")
    async def filter_switch(self, event: AstrMessageEvent):
        chain1 = [Plain(f"过滤已经启动"), Face(id=337)]
        chain2 = [Plain(f"过滤已经关闭"), Face(id=337)]
        self.flag2 = not self.flag2
        if self.flag2:
            yield event.chain_result(chain1)
        else:
            yield event.chain_result(chain2)

    @filter.command("text")
    async def text_switch(self, event: AstrMessageEvent):
        user_id = event.get_sender_id()
        chain1 = [Plain(f"文本已经启动"), Face(id=337)]
        chain2 = [Plain(f"文本已经关闭"), Face(id=337)]
        self.flag = not self.flag
        if self.flag:
            yield event.chain_result(chain1)
        else:
            yield event.chain_result(chain2)

    async def generate_voice(self,text: str, model: str):
        # API地址
        url = "http://uapi.dxx.gd.cn/voice/add"
        speed_factor = 1.0  # 语速，取值范围0.5-1.5，默认值为1.0。
        types = "url"  # 音频返回形式，仅支持url和base64，默认值为"url"。
        # 请求参数
        payload = {
            "text": text,
            "model": model,
            "speed_factor": speed_factor,
            "type": types
        }
        result = MessageChain()
        result.chain = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json(content_type=None)
                        if data.get("code") == 200:
                            # 根据返回类型处理结果
                            if payload["type"] == "url":
                                output_audio_path = data.get('url')
                                return output_audio_path
                            else:
                                result.chain.append(Plain(f"语音生成失败: {result}"))
                                return result
                        else:
                            result.chain.append(Plain(f"语音生成失败: {result}"))
                            return result
                    else:
                        print(f"HTTP Error: {response.status}")
        except aiohttp.ClientError as e:
            print(f"Request failed: {str(e)}")
        except Exception as e:
            print(f"Error occurred: {str(e)}")

    def load_ttsrooms(self):
        dicts = []
        with open(self.tts_path, 'r') as f:
            for line in f:
                dicts.append(json.loads(line.strip()))
        # 分配到各自的字典
        if not dicts:  # 如果 dicts 为空
            logger.warning("加载的数据为空")
            return
        else:
            self.ttsrooms = dicts[0]
            return

    def save_ttsrooms(self):
        with open(self.tts_path, 'w') as f:
            f.write(json.dumps(self.ttsrooms) + '\n')