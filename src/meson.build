conf = configuration_data()
conf.set('PYTHON', py_installation.full_path())
conf.set('VERSION', meson.project_version())
conf.set('APP_ID', application_id)
conf.set('PKGDATA_DIR', pkgdatadir)

configure_file(
  input: 'ztdeck.in',
  output: 'ztdeck',
  configuration: conf,
  install: true,
  install_dir: bindir,
  install_mode: 'rwxr-xr-x',
)

sources = [
  '__init__.py',
  'main.py',
  'client.py',
  'window.py',
  'networks.py',
  'peers.py',
  'setup_view.py',
  'util.py',
]

install_data(sources, install_dir: pkgdatadir / 'ztdeck')
