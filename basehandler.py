import os


class BaseHandler:

	description = ""
	options = []

	def attach_arguments(self, argparser):
		pass

	def check_parameters(self, args):
		pass

	def early_validation(self, path, data):
		pass

	def handle(self, data):
		pass
