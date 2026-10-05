{
  buildPythonApplication,
  lib,
  psutil,
  ruamel-yaml,
  setuptools,
}:
buildPythonApplication (final: {
  pname = "dripfetch";
  version = (lib.importTOML ./pyproject.toml).project.version;
  pyproject = true;
  src = ./.;

  build-system = [ setuptools ];

  dependencies = [
    ruamel-yaml
    psutil
  ];

  pythonImportsCheck = [ "dripfetch" ];

  meta = {
    description = "A customizable terminal system information display with animated rain.";
    homepage = "https://github.com/a-shygun/dripfetch";
    license = lib.licenses.mit;
    mainProgram = "dripfetch";
  };

})
