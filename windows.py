import browser
import settings

def init():
  base_url = "http://www.facebook.com"
  base_url_override = settings.get_setting("BaseUrl")
  if (base_url_override):
    print("BaseUrl:", base_url_override)
    base_url = base_url_override

  global main_window, chat_window
  main_window = browser.BrowserWindow(base_url + "/desktop/client/")
  main_window.resize(212, 640)
  main_window.show()

  chat_window = browser.BrowserWindow(base_url + "/desktop/client/chat.php")
  chat_window.resize(420, 340)
