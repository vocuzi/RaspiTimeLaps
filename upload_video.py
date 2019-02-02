import http.client as httplib
import httplib2
import os
import random
import sys
import time
import io

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


class VideoUpload:

	def __init__(self,args):
		httplib2.RETRIES = 1
		self.MAX_RETRIES = 10
		self.RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error,
			IOError,
			httplib.NotConnected,
			httplib.IncompleteRead,
			httplib.ImproperConnectionState,
			httplib.CannotSendRequest,
			httplib.CannotSendHeader,
			httplib.ResponseNotReady,
			httplib.BadStatusLine)
		self.MISSING_CLIENT_SECRETS_MESSAGE = "MISSING CLIENT_SECRETS_FILE"
		self.RETRIABLE_STATUS_CODES = [500,502,503,504]
		self.CLIENT_SECRETS_FILE = "client_secrets.json"
		self.YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
		self.YOUTUBE_API_SERVICE_NAME = "youtube"
		self.YOUTUBE_API_VERSION = "v3"
		self.PRIVACY_STATUSES = ("public","private","unlisted")
		self.args = args

	def get_authenticated_service(self):
		flow = flow_from_clientsecrets(self.CLIENT_SECRETS_FILE,
			scope=self.YOUTUBE_UPLOAD_SCOPE,
			message=self.MISSING_CLIENT_SECRETS_MESSAGE)
		storage = Storage("uv-oauth2.json")
		credentials = storage.get()

		if credentials is None or credentials.invalid:
			credentials = run_flow(flow, storage, self.args)

		return build(self.YOUTUBE_API_SERVICE_NAME,
			self.YOUTUBE_API_VERSION,
			http=credentials.authorize(httplib2.Http()))

	def initialize_upload(self,authorization):
		media = MediaFileUpload(args.file, chunksize=-1, resumable=True)
		tags = None

		if args.keywords:
			tags = args.keywords.split(",")

		body = dict(
			snippet=dict(
				title=self.args.title,
				description=self.args.description,
				tags=tags,
			),
			status=dict(
				privacyStatus=self.args.privacyStatus
			)
		)
		
		videos_insert_req = authorization.videos().insert(
			part=",".join(body.keys()),
			body=body,
			media_body=media,
		)

		self.resumable_upload(videos_insert_req)

	def resumable_upload(self,videos_insert_req):
		response = None
		error = None
		retry = 0
		while response is None:
			try:
				# uploading file
				status, response = videos_insert_req.next_chunk()
				if 'id' in response:
					return response["id"]
				else:
					return response
			except HttpError as e:
				if e.resp.status in RETRIABLE_STATUS_CODES:
					error = "retriable_status_error"
				else:
					raise
			except (RETRIABLE_EXCEPTIONS, e):
				error = "retriable_error"

			if error is not None:
				retry+=1
				if retry > MAX_RETRIES:
					return str(e)
				max_sleep = 2 ** retry
				sleep_seconds = random.random() * max_sleep
				time.sleep(sleep_seconds)


args = argparser.parse_args()
args.title = "video-title"
args.file = "video-file-path"
args.description = "video-desc"
args.privacyStatus = "unlisted"
args.keywords = ""
video = VideoUpload(args)
authorization = video.get_authenticated_service()
uploadVideo = video.initialize_upload(authorization)
