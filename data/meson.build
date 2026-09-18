desktop_conf = configuration_data()
desktop_conf.set('APP_ID', application_id)

# Two stages: configure_file substitutes @APP_ID@, then i18n.merge_file folds
# in the translations from po/. Meson's i18n module only accepts a plain .in
# file as input, hence the .in.in sources.
desktop_in = configure_file(
  input: 'io.github.ygtadk.ZTDeck.desktop.in.in',
  output: application_id + '.desktop.in',
  configuration: desktop_conf,
)

desktop_file = i18n.merge_file(
  input: desktop_in,
  output: application_id + '.desktop',
  type: 'desktop',
  po_dir: meson.project_source_root() / 'po',
  install: true,
  install_dir: datadir / 'applications',
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

metainfo_in = configure_file(
  input: 'io.github.ygtadk.ZTDeck.metainfo.xml.in.in',
  output: application_id + '.metainfo.xml.in',
  configuration: desktop_conf,
)

metainfo_file = i18n.merge_file(
  input: metainfo_in,
  output: application_id + '.metainfo.xml',
  type: 'xml',
  po_dir: meson.project_source_root() / 'po',
  install: true,
  install_dir: datadir / 'metainfo',
)

appstream_util = find_program('appstreamcli', required: false)
if appstream_util.found()
  test('Validate appstream file', appstream_util,
       args: ['validate', '--no-net', '--explain', metainfo_file])
endif

install_data(
  'icons/hicolor/scalable/apps/io.github.ygtadk.ZTDeck.svg',
  install_dir: datadir / 'icons/hicolor/scalable/apps',
)

install_data(
  'icons/hicolor/symbolic/apps/io.github.ygtadk.ZTDeck-symbolic.svg',
  install_dir: datadir / 'icons/hicolor/symbolic/apps',
)
