{ buildPythonPackage, setuptools, gitRev ? "unknown", gitDate ? "unknown" }:

buildPythonPackage {
  pname = "ham";
  version = "0.1.0";
  pyproject = true;

  src = ./..;

  build-system = [ setuptools ];

  pythonImportsCheck = [ "ham" ];

  preBuild = ''
    substituteInPlace ham/_version.py \
      --subst-var-by GIT_REV "${gitRev}" \
      --subst-var-by GIT_DATE "${gitDate}"
  '';
}
