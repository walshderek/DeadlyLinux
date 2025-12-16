import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow

windows_base = '/mnt/c/AI/apps/ComfyUI Desktop/custom_nodes/comfyui-google-sheets-integration'
client_secrets_file = os.path.join(windows_base, 'client_secret.json')
token_file = os.path.join(windows_base, 'token.pickle')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

print('--- REFRESHING GOOGLE TOKEN (copy/paste URL) ---')
print(f'Client Secret: {client_secrets_file}')

if not os.path.exists(client_secrets_file):
    print('❌ ERROR: client_secret.json not found!')
    raise SystemExit(1)

flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
creds = flow.run_local_server(port=0, open_browser=False)

with open(token_file, 'wb') as token:
    pickle.dump(creds, token)

print(f'✅ SUCCESS: New token saved to {token_file}')
