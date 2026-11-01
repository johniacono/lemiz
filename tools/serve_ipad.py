"""Serve the reader over HTTPS on the local network, so an iPad can install it from this Mac.
Usage: python3 serve_ipad.py [PORT]
The certificates live in ~/.lemiz-certs, outside Dropbox, so the private keys are not synced.
The certificate authority is only valid for this Mac's .local name.
"""
import functools, http.server, os, ssl, subprocess, sys

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8443
site = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
certs = os.path.expanduser("~/.lemiz-certs")
host = subprocess.check_output(["scutil", "--get", "LocalHostName"], text=True).strip() + ".local"

def run(*args):
    subprocess.run(["openssl", *args], check=True, cwd=certs, capture_output=True)

def make_certs():
    os.makedirs(certs, mode=0o700, exist_ok=True)
    with open(os.path.join(certs, "ca.cnf"), "w") as f:
        f.write(f"""[req]
distinguished_name = dn
x509_extensions = ca
prompt = no
[dn]
CN = Les Miserables local CA ({host})
[ca]
basicConstraints = critical, CA:TRUE, pathlen:0
keyUsage = critical, keyCertSign, cRLSign
nameConstraints = critical, permitted;DNS:{host}
""")
    with open(os.path.join(certs, "server.cnf"), "w") as f:
        f.write(f"""basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = DNS:{host}
""")
    run("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "3650", "-keyout", "ca.key", "-out", "lemiz-ca.crt", "-config", "ca.cnf")
    run("req", "-newkey", "rsa:2048", "-nodes", "-keyout", "server.key", "-out", "server.csr", "-subj", f"/CN={host}")
    run("x509", "-req", "-in", "server.csr", "-CA", "lemiz-ca.crt", "-CAkey", "ca.key", "-CAcreateserial", "-days", "800", "-out", "server.crt", "-extfile", "server.cnf")
    os.chmod(os.path.join(certs, "ca.key"), 0o600)
    os.chmod(os.path.join(certs, "server.key"), 0o600)

if not os.path.exists(os.path.join(certs, "server.crt")):
    make_certs()

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=site)
server = http.server.ThreadingHTTPServer(("", port), handler)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(os.path.join(certs, "server.crt"), os.path.join(certs, "server.key"))
server.socket = ctx.wrap_socket(server.socket, server_side=True)
print(f"Certificate to AirDrop: {os.path.join(certs, 'lemiz-ca.crt')}")
print(f"Address for the iPad:   https://{host}:{port}/index.html")
print("Ctrl-C to stop.", flush=True)
server.serve_forever()
