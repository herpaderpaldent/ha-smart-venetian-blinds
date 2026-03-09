FROM mcr.microsoft.com/devcontainers/python:3.13

# Remove the Yarn repository that has an expired/missing GPG key
# This prevents apt update failures during devcontainer feature installation
RUN rm -f /etc/apt/sources.list.d/yarn.list
