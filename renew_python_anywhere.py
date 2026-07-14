import os
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.environ.get('PA_USERNAME')
PASSWORD = os.environ.get('PA_PASSWORD')

if not USERNAME or not PASSWORD:
    print("❌ Error: PA_USERNAME and PA_PASSWORD must be set")
    sys.exit(1)

BASE_URL = "https://www.pythonanywhere.com"
LOGIN_URL = f"{BASE_URL}/login/"
DASHBOARD_URL = f"{BASE_URL}/user/{USERNAME}/webapps/"
TASKS_PAGE_URL = f"{BASE_URL}/user/{USERNAME}/tasks_tab/"
TASKS_API_URL = f"{BASE_URL}/api/v0/user/{USERNAME}/schedule/"


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
        return False
    if "login" in response.url.lower():
        print("❌ Login failed - still on login page")
        return False

    print("✅ Login successful")
    return True


def get_webapp_expiry(soup, domain):
    """Extracts the expiry date from the specific webapp's tab pane."""
    pane_id = f"id_{domain.replace('.', '_')}"
    pane = soup.find(id=pane_id)
    if pane:
        expiry_elem = pane.find('p', class_='webapp_expiry')
        if expiry_elem and expiry_elem.find('strong'):
            return expiry_elem.find('strong').text.strip()
    return "Unknown Date"


def renew_webapps(session):
    print("📊 Checking web apps...")
    time.sleep(1)
    dashboard = session.get(DASHBOARD_URL, timeout=10)
    dashboard.raise_for_status()
    soup = BeautifulSoup(dashboard.content, 'html.parser')

    forms = [f for f in soup.find_all('form', action=True) if '/extend' in f['action'].lower()]
    renewed_details = []

    if not forms:
        print("ℹ️ No web apps found on this account.")
        return True, renewed_details

    ok = True
    for form in forms:
        action = urljoin(BASE_URL, form['action'])
        domain = action.rstrip('/').split('/webapps/')[-1].replace('/extend', '')
        csrf = form.find('input', {'name': 'csrfmiddlewaretoken'})
        
        if not csrf:
            print(f"❌ No CSRF token for {domain}, skipping")
            ok = False
            continue

        # Get old expiry date directly from the HTML structure
        old_expiry = get_webapp_expiry(soup, domain)

        r = session.post(
            action,
            data={'csrfmiddlewaretoken': csrf['value']},
            headers={'Referer': DASHBOARD_URL},
            timeout=10
        )
        
        if r.status_code == 200 and 'webapps' in r.url.lower():
            # Fetch dashboard again to extract the New Expiry Date
            time.sleep(1)
            dash_after = session.get(DASHBOARD_URL, timeout=10)
            soup_after = BeautifulSoup(dash_after.content, 'html.parser')
            
            new_expiry = get_webapp_expiry(soup_after, domain)

            detail = f"Web App: {domain} ({old_expiry} → {new_expiry})"
            print(f"✅ Renewed web app: {domain} ({old_expiry} → {new_expiry})")
            renewed_details.append(detail)
        else:
            print(f"❌ Failed to renew web app: {domain} (status {r.status_code})")
            ok = False

    print(f"📋 Web apps renewed: {len(renewed_details)}")
    return ok, renewed_details


def renew_scheduled_tasks(session):
    print("🗓️ Checking scheduled tasks...")
    time.sleep(1)
    csrftoken = session.cookies.get('csrftoken')
    r = session.get(TASKS_API_URL, headers={'Referer': TASKS_PAGE_URL}, timeout=10)

    renewed_details = []

    if r.status_code != 200:
        print(f"❌ Could not fetch scheduled tasks (status {r.status_code})")
        return False, renewed_details

    try:
        tasks = r.json()
    except ValueError:
        print("❌ Scheduled tasks response was not valid JSON")
        return False, renewed_details

    if not tasks:
        print("ℹ️ No scheduled tasks found on this account.")
        return True, renewed_details

    ok = True
    for task in tasks:
        extend_url = task.get('extend_url')
        desc = task.get('command') or f"task {task.get('id')}"
        old_expiry = task.get('expiry')
        
        if not extend_url:
            continue
            
        resp = session.post(
            urljoin(BASE_URL, extend_url),
            headers={'X-CSRFToken': csrftoken, 'Referer': TASKS_PAGE_URL},
            timeout=10
        )
        
        if resp.status_code == 200:
            # Re-fetch task list to guarantee we get the updated expiry from the API
            time.sleep(1)
            r_after = session.get(TASKS_API_URL, headers={'Referer': TASKS_PAGE_URL}, timeout=10)
            new_expiry = old_expiry
            try:
                tasks_after = r_after.json()
                new_expiry = next((t.get('expiry') for t in tasks_after if t.get('id') == task.get('id')), old_expiry)
            except ValueError:
                pass
                
            if new_expiry != old_expiry:
                detail = f"Task: {desc} ({old_expiry} → {new_expiry})"
                print(f"✅ Renewed scheduled task: {desc} ({old_expiry} → {new_expiry})")
                renewed_details.append(detail)
            else:
                print(f"⚠️ Task {desc} returned 200 but expiry unchanged ({old_expiry}) — check manually")
                ok = False
        else:
            print(f"❌ Failed to renew scheduled task: {desc} (status {resp.status_code})")
            ok = False

    print(f"📋 Scheduled tasks renewed: {len(renewed_details)}")
    return ok, renewed_details


def renew():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    try:
        if not login(session):
            return False

        webapps_ok, webapps_renewed = renew_webapps(session)
        tasks_ok, tasks_renewed = renew_scheduled_tasks(session)
        
        all_renewed = webapps_renewed + tasks_renewed
        
        # Write the details to a summary file for GitHub Actions to read
        with open("renewal_summary.txt", "w", encoding="utf-8") as f:
            if all_renewed:
                for item in all_renewed:
                    f.write(f"- {item}\n")
            else:
                f.write("- No items required renewal today.\n")

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