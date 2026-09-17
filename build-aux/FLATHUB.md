# Submitting ZTDeck to Flathub

## 1. Tag a release

Flathub refuses branch-based sources: the manifest must pin an exact tag *and*
its commit SHA.

```bash
git tag -a v0.1.0 -m "ZTDeck 0.1.0"
git push origin v0.1.0
git rev-parse v0.1.0^{commit}
```

Put that SHA into `build-aux/flathub/io.github.ygtadk.ZTDeck.yml`, replacing
`REPLACE_WITH_TAG_COMMIT_SHA`, and make sure the `<release>` version in
`data/io.github.ygtadk.ZTDeck.metainfo.xml.in` matches the tag.

## 2. Verify locally before opening the PR

```bash
# Build exactly the manifest that will be submitted
flatpak run org.flatpak.Builder --user --force-clean --disable-rofiles-fuse \
    --repo=repo --mirror-screenshots-url=https://dl.flathub.org/media \
    build build-aux/flathub/io.github.ygtadk.ZTDeck.yml

flatpak run --command=flatpak-builder-lint org.flatpak.Builder \
    manifest build-aux/flathub/io.github.ygtadk.ZTDeck.yml
flatpak run --command=flatpak-builder-lint org.flatpak.Builder repo repo
```

The `manifest` check must be completely silent.

The `repo` check reports two errors on any local build:

- `appstream-external-screenshot-url`
- `appstream-remote-icon-not-mirrored`

Both are expected outside Flathub's infrastructure. They mean "this media is not
served from `dl.flathub.org` yet", which only becomes true once Flathub's own
builders mirror it. Do not try to silence them locally and do not request a
linter exception for them.

## 3. Open the pull request

Fork [`flathub/flathub`](https://github.com/flathub/flathub) and open a PR
against the **`new-pr`** branch (not `master`) containing only
`io.github.ygtadk.ZTDeck.yml` at the repository root.

A bot builds the submission and comments with the result; a human reviewer
follows. After the PR is merged, Flathub creates a dedicated
`flathub/io.github.ygtadk.ZTDeck` repository — subsequent releases are PRs
against that repo, not this one.

## 4. Get the app verified

Because the app ID is `io.github.ygtadk.ZTDeck` and the source lives at
`github.com/ygtadk/ztdeck`, verification is automatic through GitHub: log in at
[flathub.org](https://flathub.org), open the app's developer page, and follow
the verification flow.

## Notes for reviewers

- ZTDeck does **not** bundle or run the ZeroTier daemon. It is a client for the
  service's local control API on `127.0.0.1:9993`, which is why it needs
  `--share=network`.
- The only filesystem permission is `--filesystem=~/.zeroTierOneAuthToken:ro`,
  a read-only view of a single file the user creates deliberately. The app
  never requests `--talk-name=org.freedesktop.Flatpak` or host access.
- The name and icon are deliberately not ZeroTier's, and the metainfo carries an
  explicit non-affiliation statement.
