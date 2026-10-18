# Contributing
Contributions are welcomed. The project is at an early stage, and so there are some caveats.

## General
1. **This tool is still in the early stages of development**, and the style is evolving. There are sections where the design patterns are still fluid. There are other areas where seemingly strange constructs are in place, to cater for a feature much further down the timeline. Sometimes a whole section of code will be commented out, pending confirmation that there it is not needed, and that it doesn't have some guidance as to why a later bug might appear. Please accept this and be patient with us!
2. **There are not a lot of references for the GUI patterns for this code.** The division of the logic between `QGraphicsScene` and the various `QGraphicsObjects` is still being refined. There may well be 'other' ways of doing things. In this alpha phase, the goal is to establish the overall architecture, and the interaction of all the pieces - some things will only become clear once later elements are added.
3. **GUI testing is manual**. There may be better ways of doing it, but for now, it is manual. There is a script for testing the GUI [here](https://github.com/ghillebrand/Higraph/blob/main/tests/Regression%20Test1.txt). It is not complete, but PRs need to have run through this before submission.

## Guiding Principles

### 1. Minimal Dependencies

There are many great libraries out there. But each one introduces installation and development complexity - learning curves, keeping things updated, and potential security issues. Designing out development complexity is a deliberate choice.
- **A simple development environment.** There is only one external library - `PySide6`. This is a really rich library, and so far it has quite adequately covered all the needs. 
- Focus on the outcome, not the tooling. The point of this project is to have a tool that can draw and ultimately analyse Higraphs. Hopefully the core stabilises, and coding work can focus on analysis type features. Exploring "how this new tool works" is not a priority.
- Avoid security issues from the supply chain

### 2. Easy to model in

**Be able to be modelling in 60 seconds.** If game devs can make their projects useable within 30 seconds, it can be done. This still needs work!

### 3. Extensible

**Create a tool to solve new types of problems.** The ability to write code against the drawn, interactive model is key. Either via a Python "IDLE" type interface, or via "plugins" in the `Tools` menu, or just forking the project.

### 4. Build a prototype, then tidy up
This current version is still exploring how to balance all the previous principles. Things may change, and I know there are better ways of doing and structuring some aspects. Until all the interacting pieces are in place, there is no point in optimising for either perfection, elegance or speed. There is code that will end up being replaced/ extended/ rewritten as we go along. That's OK. At this stage, the previous goals, and general good practice should be sufficient.
- Design Clearly, Optimise Late
- Fail Fast, Frequently & Forward


## AI Tools
Contributions may have been assisted by the use generative AI tools. However, the use of such tools does not change our expectations for contributor responsibility, engagement, or code quality.

Note that a number of the design patterns in Higraph are not common, and LLMs do not have the training set to be able to produce them.
The following apply to all contributions.

1. **Human ownership and accountability:**
    1. Contributors are responsible for all submitted content, regardless of whether generative AI tools were used.
    2. Contributors must be able to explain all changes during review.
    3. **Licensing:** Contributors are responsible for ensuring all submitted code complies with Higraph's licensing, regardless of whether generative AI tools were used.
2. **Disclosure:** If generative AI tools were used for substantive portions of the contribution, contributors must describe their use in the change description. This also helps downstream citations comply with academic policies that may require disclosure of genAI usage.
3. **Authentic engagement:** The pull request process is collaborative and iterative. Contributors are expected to actively engage with reviewer feedback themselves. Copying and pasting replies to / from a generative AI tool does not count as engaging with the reviewer; contributors are expected to understand the changes they are proposing, not act as message courier for a third party.

> [!IMPORTANT]
> Autonomous workflows ("agents") are not human contributors. Higraph reviewers expect to interact with the human controlling the account, or we will close the PR.
4. **Consistency with Higraph conventions and existing style:** In the context of Generative AI, this particularly means conveying information (comments, documentation, etc) in a style that Higraph uses, and that is appropriate and to the point.

> [!NOTE]
> This policy is significantly inspired by the the AstroPy ["AI-Policy"](https://github.com/astropy/astropy-project/blob/main/policies/ai-policy.md), which has additional details and references that may be useful.
