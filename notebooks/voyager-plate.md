---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: myst
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
title: Pulsars as GPS
description: >
  Let's investigate how one should read the voyager plate.
date: 2026-08-16
tags: [random, inference]
source: notebook
draft: true
---

Long ago, we flew objects really fast away from the solar system, these two objects were the voyager probes. 
These missions visited the giant planets living in the outer regions of our Solar System, and eventually, they continued 
their trip and recently ended up outside of the heliopause, making them actual interstellar objects. They are the 
furthest things made by humans in the existence, and will be so probably for a while. 

At some point, it was decided to put golden vynil disks on these ships, which contained a lot of information about Humanity.

<figure>

<div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(14rem,1fr)); gap:1rem; align-items:start">

![The gold-plated record](./voyager-plate/voyager-nasa-disk.jpg)

![The engraved cover](./voyager-plate/voyager-nasa-cover.jpg)

</div>

<figcaption>The record (left), and the cover (right). Image Credit: NASA/JPL-Caltech</figcaption>
</figure>

These symbols were engraved on the surface of the cover, and were designed to be read by extraterrestrial intelligence. 
A good exercise would be to see if they are readable by terrestrial intelligence. 