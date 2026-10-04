class Dripfetch < Formula
  include Language::Python::Virtualenv

  desc "Customizable terminal system information dashboard with animated rain"
  homepage "https://github.com/a-shygun/dripfetch"
  url "https://github.com/a-shygun/dripfetch/archive/refs/tags/v0.4.0.tar.gz"
  sha256 "e92ebe96c31330c265bc18a1d6eab1b41ab695e6207c2dc79efe5f6bd988a90c"
  license "MIT"

  depends_on "python@3.12"

  resource "psutil" do
    url "https://files.pythonhosted.org/packages/aa/c6/d1ddf4abb55e93cebc4f2ed8b5d6dbad109ecb8d63748dd2b20ab5e57ebe/psutil-7.2.2.tar.gz"
    sha256 "0746f5f8d406af344fd547f1c8daa5f5c33dbc293bb8d6a16d80b4bb88f59372"
  end

  resource "ruamel.yaml" do
    url "https://files.pythonhosted.org/packages/c7/3b/ebda527b56beb90cb7652cb1c7e4f91f48649fbcd8d2eb2fb6e77cd3329b/ruamel_yaml-0.19.1.tar.gz"
    sha256 "53eb66cd27849eff968ebf8f0bf61f46cdac2da1d1f3576dd4ccee9b25c31993"
  end

  def install
    virtualenv_install_with_resources
  end


  test do
    assert_match version.to_s, shell_output("#{bin}/dripfetch --version")
    assert_match "clock", shell_output("#{bin}/dripfetch --list-boxes")
  end
end

