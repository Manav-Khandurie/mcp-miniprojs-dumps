#!/usr/bin/env python3
"""
Simple AWS Diagram MCP Tool

This script runs the AWS Diagram MCP server directly (no Streamlit, no Docker).
It relies on the awslabs.aws-diagram-mcp-server package to handle requests.
"""

from awslabs.aws_diagram_mcp_server.server import main

if __name__ == "__main__":
    main()
