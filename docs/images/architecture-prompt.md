# Architecture infographic generation

Created with the built-in Imagegen tool, using the previous diagram as a topology reference.
The current image simplifies the styling and labels while preserving the public inference,
private management, and persistent storage paths. Reviewed against the repository configuration.

## Final prompt

```text
Use case: infographic-diagram
Asset type: clean editorial architecture diagram for a GitHub README.
Redesign the attached infographic completely. It is a factual topology reference only; discard its visual styling and layout. The current version is too busy, colorful and clip-art-like. Create a sophisticated minimal technical diagram with approximately half the text and substantially more whitespace.

Visual direction: a warm white canvas; near-black typography; hairline light gray boundaries; one muted teal accent exclusively for inference arrows, neutral charcoal for management arrows. All nodes are simple white rectangles with subtle 6px corner radius. NO gradients, colored panels, shadows, glass effects, 3D objects, stock icons, cylinders, clouds, laptop illustrations, padlocks, oversized arrows or logo. Use carefully typeset humanist sans serif labels and small monospaced port annotations. Avoid bold text everywhere: moderate weight node titles, small understated secondary labels, generous line height. Deliberate grid, roomy gutters, straight connectors with small arrowheads. Landscape approximately 1800x1100. Outer margin at least 80px. Precise spacing, impeccable typography. Restrained enough to belong in excellent software documentation.

Title top left: "CLIProxyAPI on Railway" at a modest size, NOT a giant poster headline.
Small subtitle: "Public inference. Private operations."
Below it the actual diagram fills the canvas with two rows:
Top row left to right: "API clients" → "Gateway" → "Core" → "Provider APIs".
API clients and Provider APIs are outside a single thin, lightly dashed boundary labeled "RAILWAY PROJECT". Gateway, Core and Admin (below Gateway) are inside this boundary.
No icons. A small muted label above top row says "INFERENCE".
"API clients" secondary label: "OpenAI / Anthropic"
"Gateway" secondary: "Caddy" then a small line "Allowlisted routes · Client key"
"Core" secondary: "CLIProxyAPI" then a small line "Inference + management"
"Provider APIs" secondary: "Your accounts"
Client→Gateway teal arrow caption: "HTTPS · Railway edge". Within gateway, a tiny port badge ":8080". This signifies public TLS at Railway edge, HTTP listening on gateway.
Gateway→Core teal arrow caption on two small lines: "Private HTTP :8317" / "Internal key".
Core→Provider APIs teal arrow caption: "HTTPS".
Do NOT show duplicate response arrows; request arrows are enough.

Second row, naturally aligned below clients and gateway: "Administrator" (outside boundary) → "Admin" (inside, directly below Gateway). Then a charcoal elbow arrow from Admin's right edge to the bottom-left edge of Core, with clear free space around it, no arrows through cards or text.
Small muted label at the start of second row: "MANAGEMENT".
"Administrator" secondary label: "Tailscale device".
"Admin" secondary label: "Tailscale Forwarder".
Administrator→Admin caption on two small lines: "Tailnet HTTPS :8317" / "Tailnet policy".
Admin→Core caption: "Private HTTP :8317". Place "Management password" as understated secondary text next to the core management connection.
A faint separated footer compartment INSIDE Core's card says "1 GiB persistent volume" with tiny secondary "Config + provider credentials". A similar footer compartment INSIDE Admin's card says "512 MiB persistent volume" with tiny secondary "Tailscale identity". These are storage annotations, NOT more services. Gateway has no storage. Make Core card slightly taller as needed for its volume compartment; ensure management elbow does not cross storage labels.

At the bottom, one quiet note aligned to the diagram: "Core and Admin have no public domains. Gateway health port :8081 stays private."
No other footer, badges, legend, numbering or marketing copy. Do not repeat key variable names; plain-language labels above are enough. No versions, personal domains, IDs, emails, credential values, speculative services or databases.
Technical invariants: only Gateway is exposed through Railway's public HTTPS edge; Admin is only reached over the tailnet with TLS terminated at the Forwarder; Gateway→Core and Admin→Core use private HTTP; Core talks to providers over HTTPS. Two separate persistent volumes. Preserve these facts exactly while making the diagram dramatically calmer, lighter and easier to read. Render every requested label correctly.
```
