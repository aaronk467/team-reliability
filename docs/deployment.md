# Publish a reproducible public demonstration

The container builds the Vite frontend and serves it together with the FastAPI API on one origin. From the repository root:

```sh
docker build -t responsewatch .
docker run --rm -p 8000:8000 responsewatch
```

Open `http://localhost:8000` and `http://localhost:8000/docs`. Keep demonstration data synthetic. The application does not provide a production identity, authorization, or clinical data-governance system; a public demonstration should not accept sensitive operational records.

Deploy the Docker image to a container host with HTTPS and external port 8000, following that host's deployment instructions. Confirm the public URL loads the dashboard, lists all three datasets, runs analysis, and opens the API documentation. A repository alone does not satisfy the publicly available web-tool requirement. Record the verified deployment URL in the repository description and README after deployment.

For GitHub publication, review `git status` and the proposed diff, verify no private data or credentials are included, and run the Python tests and frontend production build. Commit the source, lockfiles, synthetic CSVs, generator, and documentation to the intended repository, then push the reviewed branch. Make the repository public in its GitHub visibility settings if it is not already public, subject to the owner's authorization. Add the live demonstration URL and a short walkthrough to the README, and tag the reviewed submission commit so evaluators can reproduce the exact version. Do not commit `.env`, local virtual environments, or real dispatch logs.

A useful demonstration is: select high priority and the stable dataset; inspect the frozen first-20-day baseline; switch to the South-shift dataset and review South's post-baseline duration and late-fraction signals; then select improvement and observe lower post-baseline response times. Explain the distinction between a control limit and the response target, and show the sample sizes and uncertainty before drawing a conclusion.

## Default host: Render

The committed `render.yaml` defines one free Docker web service with `/api/health` as its health check. Connect your GitHub account at Render, create a new Blueprint from `aaronk467/team-reliability`, and approve the service creation. Render supplies the public HTTPS address after the build. Free services may sleep when inactive and take time to wake. No external database is required: analysis requests are stateless and completed-call demo additions remain in the user's browser. Do not rely on a container filesystem for operational data retention.

A hosting account is required to create the service; the repository configuration does not itself publish a running site. After creation, use the public HTTPS address to verify the three demo datasets, analysis, CSV import, and API documentation, then record that address in the README.

### Building inside a TLS-inspecting cloud workspace

The Dockerfile supports an optional BuildKit secret named `cloud_ca` containing the environment's trusted CA bundle. Supply it with `--secret id=cloud_ca,src=/etc/ssl/certs/ca-certificates.crt` when needed. The build uses that bundle only for package installation and never disables TLS verification or bakes the cloud certificate into the runtime image. A proxy-managed Docker daemon may also require explicit `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` build arguments and DNS resolution for its proxy host. These options are cloud-specific; ordinary hosting builds use the standard Docker command above.
