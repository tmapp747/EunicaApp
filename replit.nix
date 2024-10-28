{pkgs}: {
  deps = [
    pkgs.chromium
    pkgs.playwright-driver
    pkgs.gitFull
    pkgs.openssl
    pkgs.postgresql
  ];
}
