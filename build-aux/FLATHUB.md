# Submitting ZTDeck to Flathub

Everything below the "Status" section is already done for v0.1.0. What remains
is step 3, which **you have to do by hand** — see the warning there.

## Status for v0.1.0

- [x] Tagged `v0.1.0` → commit `6c932c892de964e3ddeccc70c8c98678e6fe7835`
- [x] Submission manifest pinned to that exact tag and SHA
- [x] Built straight from GitHub with the submission manifest, and it runs
- [x] `manifest` lint completely silent
- [x] Screenshots reachable over HTTPS
- [ ] Submission PR against `new-pr` — **must be opened by a human**

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
`data/io.github.ygtadk.ZTDeck.metainfo.xml.in.in` matches the tag.

## 2. Verify locally before opening the PR

Build the submission manifest from a clean directory, so it is fetched from
GitHub exactly as Flathub's builders will fetch it:

```bash
mkdir -p /tmp/fhbuild && cp build-aux/flathub/io.github.ygtadk.ZTDeck.yml /tmp/fhbuild/
cd /tmp/fhbuild
flatpak run --filesystem=/tmp/fhbuild org.flatpak.Builder --user --force-clean \
    --disable-rofiles-fuse --repo=repo \
    --mirror-screenshots-url=https://dl.flathub.org/media \
    build /tmp/fhbuild/io.github.ygtadk.ZTDeck.yml

flatpak run --filesystem=/tmp/fhbuild --command=flatpak-builder-lint \
    org.flatpak.Builder manifest /tmp/fhbuild/io.github.ygtadk.ZTDeck.yml
flatpak run --filesystem=/tmp/fhbuild --command=flatpak-builder-lint \
    org.flatpak.Builder repo /tmp/fhbuild/repo
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

> **Do this yourself. Flathub's [Generative AI
> policy](https://docs.flathub.org/docs/for-app-authors/requirements#generative-ai-policy)
> states that AI tools or agents must not open or automate Flathub submission
> pull requests, or generate their commit messages, descriptions, review
> comments, or replies. Have an assistant prepare and verify the manifest, but
> open the PR, write its description, and answer reviewers in your own words.**
>
> The same policy requires disclosing AI-generated code, documentation or
> packaging that ships in the app, identifying the affected parts and the
> approximate extent. Decide what to disclose before you submit.

```bash
gh repo fork --clone flathub/flathub && cd flathub
git checkout --track origin/new-pr
git checkout -b ztdeck-submission new-pr
cp /path/to/ztdeck/build-aux/flathub/io.github.ygtadk.ZTDeck.yml .
git add io.github.ygtadk.ZTDeck.yml
git commit      # write this message yourself
git push -u origin ztdeck-submission
```

Then open the PR on github.com against the **`new-pr`** base branch (never
`master`), titled `Add io.github.ygtadk.ZTDeck`. It must contain only
`io.github.ygtadk.ZTDeck.yml` at the repository root.

A bot builds the submission; comment `bot, build` to trigger a test build once
review comments are resolved. After the PR is merged, Flathub creates a
dedicated `flathub/io.github.ygtadk.ZTDeck` repository — subsequent releases are
PRs against that repo, not this one. Accept the write-access invitation within
a week, with 2FA enabled.

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
- The metainfo carries an explicit non-affiliation statement. Note that the
  icon does resemble ZeroTier's own branding; be ready to discuss this if a
  reviewer raises it.
