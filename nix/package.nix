{ buildPythonPackage, setuptools }:

buildPythonPackage {
  pname = "ham";
  version = "0.1.0";
  pyproject = true;

  src = ./..;

  build-system = [ setuptools ];

  pythonImportsCheck = [ "ham" ];
}
