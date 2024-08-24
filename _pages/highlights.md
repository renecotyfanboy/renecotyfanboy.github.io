---
title: Highlights
permalink: /highlights/
---

Here you will find some of the projects I've worked on. Click on the repository links to explore the repositories.

<div class="portfolio">
  <div class="project">
    <div class="project-content">
      <img src="{{ site.url }}{{ site.baseurl }}/assets/images/jaxspec_logo_small.svg" alt="JaxSpec logo" class="project-image">
      <div>
        <h3><a href="https://github.com/renecotyfanboy/jaxspec">jaxspec</a></h3>
        <p>My current research project, which is a library for X-ray spectral fitting built on JAX. It enables the use of Hamiltonian Monte Carlo for sampling posterior distributions, as well as Variational Inference and other machine learning approaches, while being pure Python and easy to install and use.</p>
      </div>
    </div>
  </div>
  
  <div class="project">
    <div class="project-content">
      <img src="{{ site.url }}{{ site.baseurl }}/assets/images/chainconsumer_logo.png" alt="ChainConsumer logo" class="project-image">
      <div>
        <h3><a href="https://github.com/Samreay/ChainConsumer">ChainConsumer</a></h3>
        <p>I am a maintainer of ChainConsumer, which is a Python package that allows for the visualization and analysis of Markov Chain Monte Carlo (MCMC) chains. </p>
      </div>
    </div>
  </div>
  
  <div class="project">
    <div class="project-content">
      <img src="{{ site.url }}{{ site.baseurl }}/assets/images/lol_logo.png" alt="League Project logo" class="project-image">
      <div>
        <h3><a href="https://github.com/renecotyfanboy/leagueProject">Data analysis in League of Legends</a></h3>
        <p>I've played a lot of League of Legends back in the day. As a side project, I used statistical inference and modelling to investigate the dynamics of LoL players, showing the overall balance of the game using thousands of matches.</p>
      </div>
    </div>
  </div>
</div>

<style>
.portfolio {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.project {
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background-color: #f9f9f9;
}

.project-content {
  display: flex;
  align-items: flex-start;
}

.project-image {
  width: 50px;
  height: 50px;
  margin-right: 15px;
  border-radius: 4px;
}

.project h3 {
  margin-top: 0;
}

.project p {
  margin-bottom: 0;
}
</style>
