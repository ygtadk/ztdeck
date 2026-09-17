desktop_conf = configuration_data()
desktop_conf.set('APP_ID', application_id)

desktop_file = configure_file(
  input: 'io.github.ygtadk.ZTDeck.desktop.in',
  output: application_id + '.desktop',
  configuration: desktop_conf,
  install: true,
  install_dir: datadir / 'applications',
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

metainfo_file = configure_file(
  input: 'io.github.ygtadk.ZTDeck.metainfo.xml.in',
  output: application_id + '.metainfo.xml',
  configuration: desktop_conf,
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
