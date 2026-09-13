from twocaptcha import TwoCaptcha
import sys
import random
import json
import os
import requests
import http.cookies
import time
from dotenv import load_dotenv
from .questions import questions
from telegram.notify import send_source_notification

load_dotenv()

# 2Captcha 验证失败时最多重试次数（含首次，默认 3 次）
MAX_CAPTCHA_RETRIES = 3

class OnePointThreeAcres:
	def __init__(self, cookie: str, solver: TwoCaptcha):
		self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
		self.cf_capcha_site_key = "0x4AAAAAAAA6iSaNNPWafmlz"
		# daily checkin
		self.checkin_page = "https://www.1point3acres.com/next/daily-checkin"
		self.post_checkin_url = "https://api.1point3acres.com/api/users/checkin"
		# daily question
		self.question_page = "https://www.1point3acres.com/next/daily-question"
		self.post_answer_url = "https://api.1point3acres.com/api/daily_questions"
		self.cookie = cookie
		self.solver = solver
		self.messages = []
		self.session = requests.session()
		self.session.cookies.update(http.cookies.SimpleCookie(self.cookie))
		self.header = {
			"User-Agent": self.user_agent,
			"Content-Type": "application/json",
			"Referer": "https://www.1point3acres.com/"
		}
		self.random_say = [
			"加油加油加油加油",
			"发疯发疯发疯发疯",
			"现在!立刻!今天!开始摆烂!!!",
			"我也行，我真的行",
			"别想那么多，先活着",
			"这年头不卷也得活",
			"我不是废物，我只是累了",
			"冲冲冲，别犹豫了",
			"有工作就行，别内耗了",
			"先拿到钱，再说别的",
			"我想躺平，但我还挺住",
			"别他妈想太多了",
			"我不是不行，我只是需要换个状态",
			"现在就往前走，别停",
			"该卷的时候卷，该摆烂的时候摆烂",
			"我已经不是以前那样了",
			"别想复杂了，先过今天",
			"我可以不强，但不能崩",
			"今天也要硬着头皮上",
			"不想卷了，但我得继续",
			"我已经找到工作了，别再自我否定",
			"不是所有人都要挣扎到死",
			"不卷也能活，卷也得活",
			"我可能不强，但我不弱",
			"管别人怎么想，先把自己养好",
			"我现在比以前清醒多了",
			"别想太多，先搞定今天",
			"我不需要最卷，够用就行",
			"摆烂不如调整，调整后再冲",
			"这不是结束，这是开始",
			"我真的累了，但我还没结束",
			"有点想发疯，但我还在撑",
			"我不需要融入任何赛道",
			"我不是没用，我只是没爆发",
			"先把工作做好，再说",
			"别太认真，生活本来就难",
			"我已经拿到结果了，继续走",
			"焦虑正常，但不能停",
			"今天不行，明天继续",
			"我有点想摆烂，但我还得上",
			"路还长，别急着结束",
			"我不是输给天赋，我只是还没发力",
			"先活着，再想成为谁",
			"我也不是没价值，只是累了",
			"别卷得太狠，生活还在等你",
			"我不需要解释，先往前走",
			"不是所有天赋都得在一条路上",
			"我能撑住，我一定能撑住",
			"这年头不想卷也得卷一点",
			"我不需要证明自己有多强",
			"今天就这样，明天再说",
			"加油加油，别在这儿停住",
			"什么时候可以拿到大结果!!!!"
		]


	def _solve_turnstile(self, page_url: str) -> dict:
		"""Solve a Cloudflare Turnstile captcha, returning the result dict."""
		return self.solver.turnstile(
			sitekey=self.cf_capcha_site_key,
			url=page_url,
			useragent=self.user_agent,
		)

	def _is_captcha_error(self, response_text: str) -> bool:
		"""Check whether a 1point3acres API response indicates a captcha failure."""
		return "人机验证出错" in response_text

	def daily_checkin(self) -> bool:
		for attempt in range(1, MAX_CAPTCHA_RETRIES + 1):
			if attempt > 1:
				sleeptime = random.uniform(3, 8)
				print(f"  [Retry] checkin attempt {attempt}/{MAX_CAPTCHA_RETRIES} (sleep {sleeptime:.1f}s)", flush=True)
				time.sleep(sleeptime)

			result = self._solve_turnstile(self.checkin_page)
			code = result["code"]
			# Restriction: 您的今日想说内容少于6个字母或3个中文字，请修改后再次提交！
			emoji_list = ['kx', 'ng', 'ym', 'wl', 'nu', 'ch', 'fd', 'yl', 'shuai']
			body = {
				"qdxq": random.choice(emoji_list),
				"todaysay": random.choice(self.random_say),
				"captcha_response": code,
				"hashkey": "",
				"version": 2
			}

			response = self.session.post(self.post_checkin_url, headers=self.header, data=json.dumps(body))
			if response.status_code != 200:
				print(response.text, flush=True)
				continue

			resp_json = json.loads(response.text)
			if self._is_captcha_error(response.text):
				print(f"  Checkin captcha error (attempt {attempt}): {resp_json.get('msg')}", flush=True)
				continue

			self.messages.append(resp_json.get("msg", ""))
			return True

		print("Check-in failed after all retries", flush=True)
		self.messages.append("Check-in failed: captcha verification error after retries")
		return False

	def get_daily_task_answer(self) -> tuple[int, int]:

		print("Get daily question from 1point3acres")
		response = self.session.get(self.post_answer_url, headers=self.header)
		resp_json = json.loads(response.text)
		if resp_json["errno"] != 0 or resp_json["msg"] != "OK":
			print(response.text)
			# example response:
			# {
			# 	"errno": 0,
			# 	"msg": "OK",
			# 	"question": {
			# 		"a1": "直接告诉对方自己目前薪酬，让对方看着良心办",
			# 		"a2": "拿地里抖包袱版的工资数字要对方match",
			# 		"a3": "开一个天价，谈不拢就散伙",
			# 		"a4": "精读工资谈判宝典：https://www.1point3acres.com/bbs/thread-286214-1-1.html 知己知彼，百战不殆",
			# 		"id": 9,
			# 		"qc": "谈判工资时，哪种做法有利于得到更大的包裹？"
			# 	}
			# }
			return None, None
		# resolve the json response
		question_id = resp_json["question"]["id"]
		question = resp_json["question"]["qc"]
		question = question.strip()
		print(f"The question of 1point3acres is: {question}")
		answers = {}
		answers[1] = resp_json["question"]["a1"]
		answers[2] = resp_json["question"]["a2"]
		answers[3] = resp_json["question"]["a3"]
		answers[4] = resp_json["question"]["a4"]
		print(f"The options of 1point3acres are: {answers}")
		answer = ""
		answer_id = 0
		if question in questions.keys():
			answer = questions[question]
			for k in answers:
				if answers[k] in answer:
					# print(f"find answer: {answers[k]} option value: {k} ")
					answer_id = k
			if answer_id == "":
				print(f"The question: {question}")
				print(f"answer not found: {answer}")
				print("欢迎提交 PR 更新问题到 question.py https://github.com/timerring/daily-actions")
				self.messages.append(f"Answer not found: {answer}")
		else:
			print("question not found")
			self.messages.append("Daily question not found")
			return None, None
		return question_id, answer_id

	def answer_daily_question(self, question: int, answer: int) -> bool:
		for attempt in range(1, MAX_CAPTCHA_RETRIES + 1):
			if attempt > 1:
				sleeptime = random.uniform(3, 8)
				print(f"  [Retry] answer attempt {attempt}/{MAX_CAPTCHA_RETRIES} (sleep {sleeptime:.1f}s)", flush=True)
				time.sleep(sleeptime)

			result = self._solve_turnstile(self.question_page)
			code = result["code"]
			captcha_id = result["captchaId"]

			body = {
				"qid": question,
				"answer": answer,
				"captcha_response": code,
				"hashkey": "",
				"version": 2
			}

			response = self.session.post(self.post_answer_url, headers=self.header, data=json.dumps(body))

			if self._is_captcha_error(response.text):
				print(f"  Answer captcha error (attempt {attempt})", flush=True)
				self.solver.report(captcha_id, False)
				continue

			self.solver.report(captcha_id, True)

			resp_json = json.loads(response.text)
			print(resp_json.get("msg", ""), flush=True)
			self.messages.append(resp_json.get("msg", ""))
			if resp_json.get("errno") == 0:
				return True
			elif resp_json.get("msg") == "您今天已经答过题了":
				return True
			else:
				print(response.text, flush=True)
				continue

		print("Answer failed after all retries", flush=True)
		self.messages.append("Answer failed: CAPTCHA verification error after retries")
		return False


if __name__ == "__main__":
	cookie = os.environ.get('ONEPOINT3ACRES_COOKIE').strip()
	cookie2 = os.environ.get('ONEPOINT3ACRES_COOKIE_2').strip()
	TwoCaptcha_apikey = os.environ.get('TWOCAPTCHA_APIKEY').strip()
	messages = []
	exit_code = 0
	acres = None
	
	try:
		if not cookie:
			raise ValueError("Environment variable ONEPOINT3ACRES_COOKIE is not set")
		if not cookie2:
			raise ValueError("Environment variable ONEPOINT3ACRES_COOKIE_2 is not set")
		if not TwoCaptcha_apikey:
			raise ValueError("Environment variable TWOCAPTCHA_APIKEY is not set")
		
		# initialize the solver
		solver = TwoCaptcha(TwoCaptcha_apikey)
		print("[INFO] initialize solver")
		
		# For Account 1
		# Create the instance
		print("[INFO] start Account 1")
		acres = OnePointThreeAcres(cookie, solver)

		# daily checkin
		print("[INFO] Account 1: daily_checkin()")
		daily_checkin_status = acres.daily_checkin()
		print(f"[INFO] Account 1 daily_checkin_status={daily_checkin_status}")
		if not daily_checkin_status:
			raise ValueError("Fail to check in the 1point3acres (1st account)")
		# daily question
		print("[INFO] Account 1: get_daily_task_answer()")
		question_id, answer_id = acres.get_daily_task_answer()
		print(f"[INFO] Account 1 question_id={question_id}, answer_id={answer_id}")
		# if not question_id or not answer_id:
		# 	raise ValueError("Fail to get daily question for 1st account)")
		time.sleep(random.uniform(1, 50))
		print("[INFO] Account 1: answer_daily_question()")
		answer_daily_question_status = acres.answer_daily_question(question_id, answer_id)
		print(f"[INFO] Account 1 answer_daily_question_status={answer_daily_question_status}")


		# For Account 2
		# Create the instance
		print("[INFO] start Account 2")
		acres2 = OnePointThreeAcres(cookie2, solver)

		# daily checkin
		print("[INFO] Account 2: daily_checkin()")
		daily_checkin_status2 = acres2.daily_checkin()
		print(f"[INFO] Account 2 daily_checkin_status={daily_checkin_status2}")
		# if not daily_checkin_status2:
		# 	raise ValueError("Fail to check in the 1point3acres (2nd account)")
		# daily question
		print("[INFO] Account 2: get_daily_task_answer()")
		question_id2, answer_id2 = acres2.get_daily_task_answer()
		print(f"[INFO] Account 2 question_id={question_id2}, answer_id={answer_id2}")
		# if not question_id2 or not answer_id2:
		# 	raise ValueError("Fail to get daily question for 2nd account")
		time.sleep(random.uniform(1, 50))
		print("[INFO] Account 2: answer_daily_question()")
		answer_daily_question_status2 = acres2.answer_daily_question(question_id2, answer_id2)
		print(f"[INFO] Account 2 answer_daily_question_status={answer_daily_question_status2}")


		# if not answer_daily_question_status and not answer_daily_question_status2:
		# 	raise ValueError("Fail to answer daily question for both two accounts")
		# if not answer_daily_question_status:
		# 	raise ValueError("Fail to answer daily question for 1st account")
		# if not answer_daily_question_status2:
		# 	raise ValueError("Fail to answer daily question for 2nd account")
		
	except Exception as err:
		print(err, flush=True)
		messages.append(f"Error: {err}")
		exit_code = 1
	finally:
		if acres:
			messages = acres.messages + messages
		send_source_notification("1POINT3ACRES", messages)

	sys.exit(exit_code)






