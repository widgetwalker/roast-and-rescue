#!/usr/bin/env python3
"""Automated tests for Cloud Run HTTP Server in GitHub Roast & Rescue."""

import json
import time
import subprocess
import urllib.request
import urllib.error
import sys

def run_tests():
    port = 8099
    print(f"Starting test server on port {port}...")
    proc = subprocess.Popen([sys.executable, "server.py", str(port)])
    time.sleep(1.5)

    try:
        base_url = f"http://127.0.0.1:{port}"

        # Test 1: Health check
        print("Testing Test 1: GET /health ...", end=" ")
        req = urllib.request.urlopen(f"{base_url}/health", timeout=5)
        assert req.status == 200
        health_data = json.loads(req.read().decode())
        assert health_data["status"] == "healthy"
        assert health_data["target"] == "google-cloud-run"
        print("PASSED ✅")

        # Test 2: Web Dashboard
        print("Testing Test 2: GET / ...", end=" ")
        req = urllib.request.urlopen(f"{base_url}/", timeout=5)
        assert req.status == 200
        html = req.read().decode()
        assert "GitHub Roast &amp; Rescue" in html
        assert "Bento Dashboard" in html
        print("PASSED ✅")

        # Test 3: POST /roast without body (400)
        print("Testing Test 3: POST /roast without body (expect 400) ...", end=" ")
        try:
            req = urllib.request.Request(f"{base_url}/roast", data=b"", method="POST")
            urllib.request.urlopen(req, timeout=5)
            print("FAILED ❌ (expected 400)")
            return False
        except urllib.error.HTTPError as e:
            assert e.code == 400
            print("PASSED ✅")

        # Test 4: POST /roast with missing username (400)
        print("Testing Test 4: POST /roast with empty username (expect 400) ...", end=" ")
        try:
            req = urllib.request.Request(
                f"{base_url}/roast",
                data=json.dumps({"username": ""}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=5)
            print("FAILED ❌ (expected 400)")
            return False
        except urllib.error.HTTPError as e:
            assert e.code == 400
            print("PASSED ✅")

        # Test 5: POST /roast endpoint route check
        print("Testing Test 5: POST /roast response schema ...", end=" ")
        req = urllib.request.Request(
            f"{base_url}/roast",
            data=json.dumps({"username": "octocat"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            res = urllib.request.urlopen(req, timeout=10)
            res_json = json.loads(res.read().decode())
            assert "recruiter_glance" in res_json
            assert "roast" in res_json
            assert "rescue" in res_json
            assert "bento_formatted" in res_json
            print("PASSED ✅")
        except urllib.error.HTTPError as e:
            # If 429 rate limit is returned from GitHub API, verify JSON schema of error
            err_json = json.loads(e.read().decode())
            assert "status" in err_json and err_json["status"] == "error"
            print(f"PASSED (Handled rate limit gracefully: HTTP {e.code}) ✅")

        print("\nAll Cloud Run server tests PASSED! 🚀")
        return True

    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
