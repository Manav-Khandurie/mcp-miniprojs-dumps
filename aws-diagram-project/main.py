# streamlit_app.py
import streamlit as st
import tempfile
import os
import subprocess
import shlex
from pathlib import Path

st.set_page_config(page_title="MCP AWS Diagram via Docker", layout="wide")

st.title("AWS Diagram (via mcp/aws-diagram Docker image)")

st.markdown(
    """
Enter your Python `diagrams` DSL below (example provided). When you click **Generate**, the app
writes the code to a temporary file, mounts that folder into the `mcp/aws-diagram` container,
runs the script inside the container, and reads back the produced `diagram.png`.
"""
)

example = '''# Example: simple AWS diagram (Diagrams DSL)
from diagrams import Diagram
from diagrams.aws.compute import EC2
from diagrams.aws.network import ELB
from diagrams.aws.database import RDS

with Diagram("Simple Web Service", filename="diagram", outformat="png", show=False):
    ELB("lb") >> EC2("web") >> RDS("db")
'''

code = st.text_area("Diagrams Python code", value=example, height=320)

col1, col2 = st.columns([1, 1])

with col1:
    output_name = st.text_input("Output filename (no extension)", value="diagram")
    image_format = st.selectbox("Output format", ["png", "svg"], index=0)
    run_button = st.button("Generate")

with col2:
    st.info("Notes:\n• This will run the `mcp/aws-diagram` Docker image. Make sure Docker is running.\n• If the container does not include Graphviz you may need to install Graphviz on the host or inside container.")
    st.write("Last container stdout / stderr will appear below after generation.")

def run_with_docker(code_str: str, output_basename: str, fmt: str):
    # Prepare temp workspace
    tmpdir = Path(tempfile.mkdtemp(prefix="mcp_diagrams_"))
    script_path = tmpdir / "diagram_code.py"
    # Write the code
    script_path.write_text(code_str, encoding="utf-8")

    # Many diagrams examples use `filename="diagram"` inside the script.
    # We'll make sure the script writes to the given filename by setting current working dir.
    # Mount tmpdir as /workspace so container writes diagram.png to that folder.
    container_workdir = "/workspace"
    host_path = str(tmpdir.resolve())

    # Construct docker run command. We mount the temp dir and run python inside the container.
    # Note: we use --rm so container cleans up after run.
    image = "mcp/aws-diagram:latest"
    cmd = f"docker run --rm -v {shlex.quote(host_path)}:{container_workdir} -w {container_workdir} {image} python {container_workdir}/diagram_code.py"

    try:
        completed = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            text=True,
            timeout=120
        )
    except Exception as e:
        return {"ok": False, "error": str(e), "stdout": "", "stderr": "" , "outpath": None}

    stdout = completed.stdout
    stderr = completed.stderr
    ok = completed.returncode == 0

    # container should have produced output file "<output_basename>.<fmt>" in tmpdir
    out_file = tmpdir / f"{output_basename}.{fmt}"
    if out_file.exists():
        return {"ok": ok, "stdout": stdout, "stderr": stderr, "outpath": str(out_file), "tmpdir": str(tmpdir)}
    else:
        # if user code created 'diagram.png' explicitly, try that too
        candidate = tmpdir / f"diagram.{fmt}"
        if candidate.exists():
            return {"ok": ok, "stdout": stdout, "stderr": stderr, "outpath": str(candidate), "tmpdir": str(tmpdir)}
        return {"ok": ok, "stdout": stdout, "stderr": stderr, "outpath": None, "tmpdir": str(tmpdir)}

if run_button:
    st.spinner("Generating...")
    result = run_with_docker(code, output_name, image_format)
    st.write("**Exit OK:**", result["ok"])
    if result["stdout"]:
        st.subheader("Container stdout")
        st.code(result["stdout"])
    if result["stderr"]:
        st.subheader("Container stderr")
        st.code(result["stderr"])

    if result["outpath"]:
        st.success(f"Diagram generated: {result['outpath']}")
        # Display image if it's a png or svg
        if image_format == "png":
            st.image(result["outpath"], use_column_width=True)
        else:
            # For svg, read and render raw HTML
            svg_data = Path(result["outpath"]).read_text()
            st.components.v1.html(svg_data, height=600)
    else:
        st.error("No output image found. Check stdout/stderr above. The container may have required additional system dependencies (Graphviz) or your code may have failed.")
