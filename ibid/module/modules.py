import re
import os

import ibid.module

pattern1 = re.compile(r'^\s*(load|unload|reload)\s+(\S+)\s*$')
pattern2 = re.compile(r'^\s*lsmod\s*$')

class Module(ibid.module.Module):

	def list(self):
		reply = ''
		for handler in self.processor.handlers:
			name = handler.__module__.split('.', 2)[2]
			reply = u'%s%s, ' % (reply, name)
		return reply

	def process(self, query):
		if not query['addressed'] or query['processed']:
			return

		reply = None

		match = pattern1.search(query['msg'])
		if match:
			(action, module) = match.groups()

			if action == u'load':
				reply = self.processor.load(module)
				reply = reply and u'Loaded %s' % module or u"Couldn't load %s" % module
			elif action == u'unload':
				reply = self.processor.unload(module)
				reply = reply and u'Unloaded %s' % module or u"Couldn't unload %s" % module
			elif action == u'reload':
				self.processor.unload(module)
				reply = self.processor.load(module)
				reply = reply and u'Reloaded %s' % module or u"Couldn't reload %s" % module

		match = pattern2.search(query['msg'])
		if match:
			reply = self.list()

		if reply:
			query['responses'].append(reply)
			query['processed'] = True
			return query
