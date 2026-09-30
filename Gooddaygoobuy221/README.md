# GooddayGoodbay221

Package version: 221

Original application:
`app/GooddayGoodbay220.exe`

Original application SHA256:

`2d59428f34a9e613c51b0b770e6839e85abb5ecd9efbf3d9a6cf2e8edc28c350`

Original protected package SHA256:

`6a15d38a988a653ced29d549fa7bdf4a5c7c7cf82a7373afe32fb9fb3012a7cb`

## Important

The original application binary is preserved byte-for-byte.

The original protected package does not contain buildable application
source code. Therefore this package does not claim to repair the internal
application implementation.

## Package control plane

- install.ps1
- uninstall.ps1
- verify.ps1
- tools/windows_runtime_test.ps1
- tools/local_validate.py
- SHA256_MANIFEST.json
- VS Code configuration
- Dev Container
- GitHub Windows verification workflow

## Verification policy

A local/static PASS does not prove Windows runtime success.

Windows runtime is PASS only when the Windows workflow produces evidence
for installation, executable launch, shortcut verification, and cleanup.
