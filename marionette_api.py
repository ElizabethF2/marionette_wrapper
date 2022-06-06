from marionette_driver.marionette import Marionette, ActionSequence, errors
from marionette_driver.by import By
from marionette_driver.keys import Keys
from marionette_driver import errors
import time, os, signal, socket, json

_CLIENT = None
_WRAPPED_CLIENT = None

_PASSTHROUGH_FUNCS = ('navigate', 'execute_script', 'get_url', 'find_element', 'find_elements', 'get_cookies', 'delete_all_cookies', 'switch_to_alert', 'page_source')

DEFAULT_INTERVAL = 0.2

class Timeout(Exception):
  pass

class ClientWrapper(object):
  def __init__(self, client):
    self.client = client

  def __getattr__(self, name):
    return getattr(self.client, name)

  def try_find_elements(self, selector):
    return self.find_elements(By.CSS_SELECTOR, selector)

  def try_find_element(self, selector, offset = 0):
    elements = self.try_find_elements(selector)
    if len(elements) > offset:
      return elements[offset]

  def wait_for_elements(self, selector, interval=DEFAULT_INTERVAL, min_count=1, visible=True, timeout=None, except_on_timeout=False):
    if timeout:
      start = time.time()
    while True:
      elements = self.try_find_elements(selector)
      if visible:
        try:
          elements = list(filter(lambda e: e.is_displayed(), elements))
        except errors.StaleElementException:
          continue
      if len(elements) >= min_count:
        return elements
      if timeout and (time.time()-start) >= timeout:
        if except_on_timeout:
          raise Timeout()
        else:
          return None
      time.sleep(interval)

  def wait_for_element(self, selector, interval=DEFAULT_INTERVAL, visible=True, timeout=None, except_on_timeout=False):
    elems = self.wait_for_elements(selector, interval=interval, visible=visible, timeout=timeout, except_on_timeout=except_on_timeout)
    if not elems and not except_on_timeout:
      return None
    return elems[0]

  def try_find_elements_with_text(self, selector, text):
    elements = []
    for e in self.try_find_elements(selector):
      try:
        if e.text == text or (type(text) != str and e.text in text):
          elements.append(e)
      except errors.StaleElementException:
        pass
    return elements

  def try_find_element_with_text(self, selector, text, offset=0):
    try:
      return self.try_find_elements_with_text(selector, text)[offset]
    except IndexError:
      return None

  def wait_for_elements_with_text(self, selector, text, min_count=1, interval=DEFAULT_INTERVAL, visible=True, timeout=None, except_on_timeout=False):
    if timeout:
      start = time.time()
    while True:
      elements = self.try_find_elements_with_text(selector, text)
      if visible:
        try:
          elements = list(filter(lambda e: e.is_displayed(), elements))
        except errors.StaleElementException:
          continue
      if len(elements) >= min_count:
        return elements
      if timeout and (time.time()-start) >= timeout:
        if except_on_timeout:
          raise Timeout()
        else:
          return None
      time.sleep(interval)

  def wait_for_element_with_text(self, selector, text, offset=0, interval=DEFAULT_INTERVAL, timeout=None, except_on_timeout=False):
    elems = self.wait_for_elements_with_text(selector, text, min_count=offset+1, interval=interval, timeout=timeout, except_on_timeout=except_on_timeout)
    if not elems and not except_on_timeout:
      return None
    return elems[offset]

  def enter_text_in_box(self, text, selector):
    self.client.find_element(By.CSS_SELECTOR, selector).tap()
    self.send_keys(text)

  def send_keys(self, keys):
    ActionSequence(self.client, "key", '').send_keys(keys).perform()

  def quit(self, sig = signal.SIGINT):
    os.kill(self.client.process_id, sig)

  def is_tor(self):
    # _CLIENT.navigate('https://check.torproject.org/')
    # assert _CLIENT.execute_script('return (document.querySelector(".on").innerText == "Congratulations. This browser is configured to use Tor.");')
    self.navigate('https://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/')
    return self.execute_script('return document.title.startsWith("DuckDuckGo");')

  def get_json_from_page_source(self, source):
    return source[source.index('<div id="json">')+15:source.rindex('</div></div>')]

  def get_json(self, url):
    self.navigate(url)
    return json.loads(self.get_json_from_page_source(self.page_source))

  def navigate_async(self, url, interval=0.1):
    eurl = json.dumps(url)
    self.execute_script(f'window.location={eurl};')


def get_or_create_client(require_tor = None):
  global _CLIENT, _WRAPPED_CLIENT
  if _CLIENT is None:
    _CLIENT = Marionette('localhost', port=2828)
    error_shown = False
    while True:
      try:
        _CLIENT.start_session()
        break
      except socket.timeout:
        if not error_shown:
          print('Please start a marionette enabled browser')
          error_shown = True

    _CLIENT.set_pref('dom.webdriver.enabled', False)
    _WRAPPED_CLIENT = ClientWrapper(_CLIENT)

    if require_tor is not None:
      assert require_tor == _WRAPPED_CLIENT.is_tor()

  return _WRAPPED_CLIENT
