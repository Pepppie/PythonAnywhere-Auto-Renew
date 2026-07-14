import os
import sys
import requests
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.environ.get('PA_USERNAME')
PASSWORD = os.environ.get('PA_PASSWORD')

if not USERNAME or not PASSWORD:
    print("❌ Error: PA_USERNAME and PA_PASSWORD must be set")
    sys.exit(1)

LOGIN_URL = "https://www.pythonanywhere.com/login/"
DASHBOARD_URL = f"https://www.pythonanywhere.com/user/{USERNAME}/webapps/"
TASKS_PAGE_URL = f"https://www.pythonanywhere.com/user/{USERNAME}/tasks_tab/"
TASKS_API_URL = f"https://www.pythonanywhere.com/api/v0/user/{USERNAME}/schedule/"


def login(session):
    print(f"🔐 Logging in as {USERNAME}...")
    login_page = session.get(LOGIN_URL, timeout=10)
    login_page.raise_for_status()
    soup = BeautifulSoup(login_page.content, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
    if not csrf_token:
        print("❌ Could not find CSRF token on login page")
        return False
    csrf_token = csrf_token['value']

    payload = {
        'csrfmiddlewaretoken': csrf_token,
        'auth-username': USERNAME,
        'auth-password': PASSWORD,
        'login_view-current_step': 'auth'
    }
    response = session.post(
        LOGIN_URL,
        data=payload,
        headers={'Referer': LOGIN_URL},
        timeout=10,
        allow_redirects=True
    )
    response.raise_for_status()

    if "Log out" not in response.text and "logout" not in response.text.lower():
        print("❌ Login failed - 'Log out' not found in response")
        print(f"Response URL: {response.url}")
        return False
    if "login" in response.url.lower():
        print("❌ Login failed - still on login page")
        return False

    print("✅ Login successful")
    return True


def renew_webapps(session):
    print("📊 Checking web apps...")
    time.sleep(1)
    dashboard = session.get(DASHBOARD_URL, timeout=10)
    dashboard.raise_for_status()
    soup = BeautifulSoup(dashboard.content, 'html.parser')

    forms = [f for f in soup.find_all('form', action=True) if '/extend' in f['action'].lower()]

    if not forms:
        print("ℹ️ No web apps found on this account.")
        return True

    ok = True
    renewed = []
    for form in forms:
        action = form['action']
        domain = action.rstrip('/').split('/webapps/')[-1].replace('/extend', '')
        csrf = form.find('input', {'name': 'csrfmiddlewaretoken'})
        if not csrf:
            print(f"❌ No CSRF token for {domain}, skipping")
            ok = False
            continue
        r = session.post(
            action,
            data={'csrfmiddlewaretoken': csrf['value']},
            headers={'Referer': DASHBOARD_URL},
            timeout=10
        )
        if r.status_code == 200 and 'webapps' in r.url.lower():
            print(f"✅ Renewed web app: {domain}")
            renewed.append(domain)
        else:
            print(f"❌ Failed to renew web app: {domain} (status {r.status_code})")
            ok = False

    print(f"📋 Web apps renewed: {', '.join(renewed) if renewed else 'none'}")
    return ok


def renew_scheduled_tasks(session):
    print("🗓️ Checking scheduled tasks...")
    time.sleep(1)
    csrftoken = session.cookies.get('csrftoken')
    r = session.get(TASKS_API_URL, headers={'Referer': TASKS_PAGE_URL}, timeout=10)

    if r.status_code != 200:
        print(f"❌ Could not fetch scheduled tasks (status {r.status_code})")
        return False

    try:
        tasks = r.json()
    except ValueError:
        print("❌ Scheduled tasks response was not valid JSON")
        return False

    if not tasks:
        print("ℹ️ No scheduled tasks found on this account.")
        return True

    ok = True
    renewed = []
    for task in tasks:
        extend_url = task.get('extend_url')
        desc = task.get('command') or f"task {task.get('id')}"
        if not extend_url:
            continue
        resp = session.post(
            f"https://www.pythonanywhere.com{extend_url}",
            headers={'X-CSRFToken': csrftoken, 'Referer': TASKS_PAGE_URL},
            timeout=10
        )
        if resp.status_code == 200:
            print(f"✅ Renewed scheduled task: {desc}")
            renewed.append(desc)
        else:
            print(f"❌ Failed to renew scheduled task: {desc} (status {resp.status_code})")
            ok = False

    print(f"📋 Scheduled tasks renewed: {', '.join(renewed) if renewed else 'none'}")
    return ok


def renew():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    try:
        if not login(session):
            return False

        webapps_ok = renew_webapps(session)
        tasks_ok = renew_scheduled_tasks(session)
        return webapps_ok and tasks_ok

    except requests.Timeout:
        print("❌ Request timed out")
        return False
    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = renew()
    sys.exit(0 if success else 1)