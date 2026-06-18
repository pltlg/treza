# Code signing & notarization

The [Build workflow](../.github/workflows/build.yml) signs the Windows binaries
and signs + notarizes the macOS app **only when the relevant secrets are
present**. Without them, builds still succeed and produce **unsigned** artifacts
(users then see SmartScreen / Gatekeeper warnings).

Signing needs certificates you must obtain — they are not free:

* **Windows:** an Authenticode code-signing certificate. A standard OV cert
  (Sectigo, DigiCert, …) signs but still needs reputation to clear SmartScreen;
  an **EV** cert clears it immediately. (Azure Trusted Signing is a cheaper
  alternative but needs a different workflow step than the one here.)
* **macOS:** an Apple **Developer ID Application** certificate, which requires a
  paid **Apple Developer Program** membership ($99/yr).

Add the following as **repository secrets**
(*Settings → Secrets and variables → Actions → New repository secret*).

## Windows

| Secret | What it is |
|---|---|
| `WIN_CERT_BASE64` | Your `.pfx` certificate, base64-encoded |
| `WIN_CERT_PASSWORD` | The `.pfx` password |

Encode the cert:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("cert.pfx")) | Set-Clipboard
```

The workflow signs `treza.exe` (before packaging) and the `treza-setup-*.exe`
installer with `signtool` and a DigiCert timestamp.

## macOS

| Secret | What it is |
|---|---|
| `APPLE_CERT_BASE64` | Developer ID Application cert (`.p12`), base64-encoded |
| `APPLE_CERT_PASSWORD` | The `.p12` password |
| `APPLE_SIGN_IDENTITY` | e.g. `Developer ID Application: Your Name (TEAMID)` |
| `APPLE_ID` | Your Apple ID email |
| `APPLE_TEAM_ID` | Your 10-character Team ID |
| `APPLE_APP_PASSWORD` | An app-specific password for `notarytool` |

Encode the cert:

```bash
base64 -i cert.p12 | pbcopy
```

The workflow imports the cert into a temporary keychain, `codesign`s
`treza.app` with the hardened runtime, submits it to **notarytool**, waits for
the result, and **staples** the ticket.

## Notes

* These recipes are standard but **untested in this repo until real certs are
  added** — expect to iterate (e.g. macOS may need per-binary signing instead of
  `--deep`).
* Never commit certificates or passwords. Only the base64/secret forms above,
  stored as encrypted Actions secrets, should ever touch the repo.
