# Publish the public TuneBench demo

The repository is prepared for Streamlit Community Cloud. Publication requires
the repository owner's hosting sign-in; no hosting account/session is available
inside the development workspace. A tested deployment configuration is not itself
a live public deployment.

## Deploy

[Open the prefilled deployment page](https://share.streamlit.io/deploy?repository=manjunadhgude%2FTuneBench&branch=main&mainModule=streamlit_app.py).

1. Sign in to Streamlit Community Cloud using your GitHub account. Authorize access
   to the TuneBench repository if requested.
2. Confirm these settings:

   | Setting | Value |
   | --- | --- |
   | Repository | `manjunadhgude/TuneBench` |
   | Branch | `main` |
   | Main file path | `streamlit_app.py` |
   | Python version in Advanced settings | `3.12` |

3. Click **Deploy**. No API keys, model downloads, paid GPU, or secrets are needed.
4. Set the deployed app's sharing/visibility to **Public** if necessary. Open its
   generated `https://…streamlit.app` URL in a private browser window to verify
   that visitors can use it without signing in.

If the prefilled link opens the general dashboard, choose **Create app / Deploy
from GitHub** and enter the same settings. Copy the generated URL after the build
finishes. Do not treat this deployment-configuration link as the website URL.

## Public and local behavior

The public entry point offers **Quick demo** and **Saved model replay**, with
explicit labels. Visitors can execute the fictional rules simulation, inspect
recorded Qwen responses, and view the evaluation/architecture tabs. Replay uses
fixed historical inputs and performs no new inference or tool execution.

The full local entry point remains `app.py`; it includes optional actual CPU
Qwen inference. The public entry point disables that memory-intensive mode and
its local-model path control. It does not download weights automatically. This
public profile is suitable for a small free server; it does not provide live LLM
inference to public visitors.

`requirements.txt` installs the package's app extra with tested runtime version
constraints from `requirements-public.lock`. An editable install retains access
to the repository's replay and evaluation artifacts. Native model, training,
browser-testing and development dependencies are not installed for hosting.

## Verify or diagnose

A healthy page should offer only the two public run modes. Run a demo status
lookup for `TB-1001`, then inspect a saved replay and the Evaluation tab. A missing
replay or report indicates that the source/artifacts or editable installation
were not included correctly.

If the deployment fails, open the Community Cloud build log and confirm Python
3.12 and `streamlit_app.py`. The deployment uses normal Streamlit-managed server
settings; no custom port or public tunnel is required. Once deployed, Community
Cloud can rebuild the app when this GitHub branch changes.

For a local reproduction, use a clean Python 3.12 environment:

```bash
uv venv /tmp/tunebench-public-venv --python 3.12
uv pip install --python /tmp/tunebench-public-venv/bin/python -r requirements.txt
/tmp/tunebench-public-venv/bin/python -m streamlit run streamlit_app.py
```

The repository's deployment verification record distinguishes local public-profile
checks from an actual completed hosted deployment. No public URL is claimed until
it exists and has been checked.
