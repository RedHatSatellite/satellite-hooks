# satellite-hooks

This repo holds hooks for Satellite, each directory is its own hook. See the sub-directories README for install instructions.

NOTE: If selinux is in enforcing mode, you will likely get denials: use `audit2why` & `audit2allow` to resolve these. Also ensure you run `restorecon -RvF /usr/share/foreman/config/hooks` after you install a Hook.

### Troubleshooting
Foreman will usually run this script as the `foreman` user, we can use `sudo -u foreman <PATH to HOOK> <EVENT> <OBJECT>` to test it.
See the [foreman_hooks documentation](https://github.com/theforeman/foreman_hooks) for information regarding foreman_hooks.
