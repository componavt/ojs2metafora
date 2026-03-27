# ojs2metafora

📚🔁🧩 OJS journal metadata to `journal3.xsd` XML converter for Metafora API workflows 🗂️🔗

> Experimental toolkit for working with Open Journal Systems (OJS) metadata and preparing it for external services.

## What is this project about?

This repository explores how to extract, transform, and package journal metadata from OJS into structured XML that can be used in various integration scenarios, including workflows related to the Metafora information system. The focus is on automating metadata processing for scholarly journals, with an emphasis on flexibility rather than a fixed architecture.

The exact scope, data model, and supported workflows are still evolving and may change significantly as the project matures.

## Key ideas (subject to change)

- Reading metadata from an existing OJS 2.x database.
- Converting that metadata into XML based on a schema compatible with Metafora (currently `journal3.xsd`).
- Providing a small, scriptable toolchain that journals can adapt to their own environments.
- Keeping deployment simple (standard Python stack, no heavy dependencies).

None of these directions are final; the project is intentionally open‑ended and exploratory.

## Status

Early experimental stage.  
APIs, folder structure, and configuration formats are **not** stable yet and may be refactored without notice.

## Who might be interested?

- Journal editors and technical staff using OJS who are exploring XML export options.
- Developers integrating OJS with national or institutional indexing systems.
- Anyone experimenting with pipelines from relational metadata to schema‑driven XML.

## Disclaimer

This project is provided “as is”, without any guarantees regarding completeness, correctness, or long‑term support.  
It is not an official tool of any platform or institution and should be used at your own discretion.
