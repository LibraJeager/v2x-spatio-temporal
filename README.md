# VEEPS — Spatio-Temporal Edge AI for V2X Traffic Forecasting

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/XGBoost-ML%20Inference-EC6B23?style=for-the-badge" alt="XGBoost" />
  <img src="https://img.shields.io/badge/Docker-Containerized-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/MQTT-Eclipse%20Mosquitto-660066?style=for-the-badge" alt="MQTT" />
  <img src="https://img.shields.io/badge/SUMO-Traffic%20Simulation-34A853?style=for-the-badge" alt="SUMO" />
</p>

## Executive Summary

**VEEPS** (**V**2X **E**dge AI for **E**arly Traffic Congestion **P**rediction using **S**patio-Temporal Signals) is a graduation project that investigates how **distributed Edge AI** can be used to forecast traffic congestion **15 minutes in advance** in **Vehicle-to-Everything (V2X)** environments.

From a systems perspective, the project combines three major engineering layers:

- **Big Data ETL** for processing large-scale SUMO simulation outputs efficiently.
- **Machine Learning inference** using **XGBoost** with carefully designed **spatio-temporal features**.
- **Edge deployment** through **Dockerized RSU-like nodes** communicating over **MQTT** for real-time inference.

From a research perspective, the central hypothesis of VEEPS is that **congestion can be detected earlier through leading indicators rather than reactive speed measurements**. Therefore, the model **removes the current speed feature (`v_mean`) entirely** and instead relies on **Follower Distance Ratio (FDR)** across both **space** and **time** as the primary predictive signal. Under this formulation, the proposed model achieved **R² = 0.8919**.

---

## Abstract

Traditional traffic estimation pipelines often rely on instantaneous speed as a dominant predictor. While effective for describing current conditions, such signals are often **reactive** and can introduce **prediction bias** when the objective is **early warning**. VEEPS addresses this limitation by proposing a **spatio-temporal forecasting architecture** in which **FDR (Follower Distance Ratio)** is treated as a **leading indicator** of imminent congestion.

The project is built on top of large-scale **SUMO** simulation data and a production-inspired **V2X edge architecture**. A memory-efficient ETL pipeline based on **streaming XML parsing (`iterparse`)** transforms **13.6 GB** of raw FCD telemetry while keeping RAM usage **below 50 MB**. On top of the extracted lane-level data, the project engineers **spatial neighbor features** and **5-minute temporal memory features** for an **XGBoost** forecasting model. The trained model is then deployed inside a **Docker container** acting as a roadside unit (**RSU**) that consumes live telemetry from an **MQTT broker** and produces near-real-time congestion warnings.

The result is a compact but production-oriented prototype that connects **data engineering**, **machine learning**, and **distributed systems architecture** into one unified V2X forecasting workflow.

---

## Research Motivation

Early traffic intervention is more valuable than late-stage detection. Once average speed visibly collapses, congestion has often already formed and mitigation options become limited. This project is motivated by the idea that:

- **Microscopic vehicle interaction signals** can reveal congestion formation earlier than macroscopic traffic-speed indicators.
- **Edge-native inference** is better aligned with V2X deployment constraints than centralized-only architectures.
- **Scalable ETL** is essential when simulation or telemetry data grows to multi-gigabyte scale.

Accordingly, VEEPS explores whether a **spatio-temporal FDR representation**, executed on **distributed edge nodes**, can provide a practical and technically sound basis for **15-minute traffic forecasting**.

---

## System Architecture

```mermaid
flowchart LR
    subgraph OFFLINE["Offline ETL Pipeline & Model Training"]
        A["SUMO FCD XML Logs\n~13.6 GB"] --> B["Streaming ETL in Python\nxml.etree.ElementTree.iterparse"]
        B --> C["Lane-level feature extraction\nvehicle_count, FDR_mean"]
        C --> D["Spatio-temporal feature engineering\nFDR_in, FDR_out, FDR_med, FDR_std"]
        D --> E["XGBoost training\n15-minute forecasting target"]
        E --> F["Trained model artifact\nmodels/veeps_spatio_temporal.json"]
    end

    subgraph ONLINE["Real-time Edge Inference"]
        G["SUMO FCD Producer\n(fcd_producer.py)"] --> H["MQTT Broker\nEclipse Mosquitto"]
        H --> I["RSU Edge AI Node\nDocker container"]
        J["Road topology\nosm.net.xml"] --> I
        F -. deployed to .-> I
        I --> K["5-minute temporal memory\nper-lane deque buffer"]
        K --> L["15-minute early warning\ncongestion risk alert"]
    end
