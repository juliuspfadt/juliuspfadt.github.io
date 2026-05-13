// ═══════════════════════════════════════════════════════════
//  CV — Julius M. Pfadt  (Typst)
// ═══════════════════════════════════════════════════════════
#import "@preview/fontawesome:0.6.0": *

// ── Page setup ─────────────────────────────────────────────
#set page(
  paper: "a4",
  margin: (x: 2.15cm, y: 2.15cm),
  footer: context {
    h(1fr)
    counter(page).display("1 / 1", both: true)
  },
)

// ── Font & text ────────────────────────────────────────────
#set text(font: "Lato", size: 11pt, lang: "en")
#set par(leading: 0.65em, justify: false)
#show link: set text(fill: rgb("#333333"))

// ── Heading style: centered text with thin rules ───────────
#show heading.where(level: 1): it => {
  v(10pt)
  block(width: 100%,
    grid(
      columns: (1fr, auto, 1fr),
      align: (horizon, center, horizon),
      line(length: 100%, stroke: 0.4pt),
      pad(x: 0.8em, text(weight: "bold", size: 0.9em, it.body)),
      line(length: 100%, stroke: 0.4pt),
    )
  )
}

// ── Constants ──────────────────────────────────────────────
#let hints-width = 2.5cm
#let entry-gap = 4pt

// ── cventry ────────────────────────────────────────────────
#let cventry(
  dates,
  title,
  subtitle: none,
  location: none,
  grade: none,
  description: none,
) = {
  grid(
    columns: (hints-width, 1fr),
    column-gutter: 1em,
    align(right, text(size: 0.9em, dates)),
    {
      strong(title)
      if subtitle != none [, #subtitle]
      if location != none [, #location]
      if grade != none [, #grade]
      if description != none {
        linebreak()
        description
      }
    },
  )
  v(entry-gap)
}

// ── cvitem ─────────────────────────────────────────────────
#let cvitem(label, content) = {
  grid(
    columns: (hints-width, 1fr),
    column-gutter: 1em,
    align(right, text(size: 0.9em, label)),
    content,
  )
  v(entry-gap)
}

// ── Contact separator ──────────────────────────────────────
#let headersep = text(fill: rgb("#444444"))[~·~]

// ════════════════════════════════════════════════════════════
//  DOCUMENT
// ════════════════════════════════════════════════════════════

// ── Header ─────────────────────────────────────────────────
#align(center)[
  #text(size: 1.6em, weight: "bold")[Julius M. Pfadt]
  #v(2pt)
  #text(size: 0.9em)[#smallcaps[Postdoctoral Researcher (University of Amsterdam) --- Co-founder #link("https://www.jasp-services.com")[JASP Services BV]]]
  #v(2pt)
  #text(size: 0.75em, fill: rgb("#444444"))[
    #fa-envelope() #link("mailto:julius.pfadt@gmail.com")[julius.pfadt\@gmail.com] #headersep
    #fa-globe() #link("https://juliuspfadt.github.io")[juliuspfadt.github.io] #headersep
    #fa-github() #link("https://github.com/juliuspfadt")[GitHub] #headersep
    #fa-google() #link("https://scholar.google.com/citations?user=Db1-WloAAAAJ")[Google Scholar] #headersep
    #fa-linkedin() #link("https://www.linkedin.com/in/juliuspfadt/")[LinkedIn] #headersep
    #fa-orcid() #link("https://orcid.org/0000-0002-0758-5502")[ORCID]
  ]
]

#set text(size: 0.95em)

// ── About ──────────────────────────────────────────────────
= About

// BEGIN GENERATED ABOUT
I am a researcher in the lab of Eric-Jan Wagenmakers at the University of Amsterdam and a former DFG Walter-Benjamin fellow. My research centers on (Bayesian) statistical modeling, in particular, psychometrics, reliability estimation, and structural equation modeling. I develop open-source tools for #link("https://jasp-stats.org")[JASP] (BFpack, Factor, Reliability, SEM) and the R package Bayesrel, and I co-founded #link("https://jasp-services.com")[JASP Services BV]. I am committed to open science and accessible methodology.
// END GENERATED ABOUT

// ── Education ──────────────────────────────────────────────
= Education

#cventry(
  [2018--2023],
  [Doctorate (summa cum laude)],
  subtitle: [Department of Psychological Research Methods],
  location: [Ulm University],
  description: [
    Project title: _The Present and Future of Reliability Analysis: Advances in Theory and Practice_ (#link("http://dx.doi.org/10.18725/OPARU-49700")[Link]) \
    Supervisor: Prof. Dr. Morten Moshagen
  ],
)

#cventry(
  [2016--2018],
  [Master of Science],
  subtitle: [Psychology],
  location: [Ulm University, Germany],
)

#cventry(
  [2012--2016],
  [Bachelor of Science],
  subtitle: [Psychology],
  location: [Ulm University, Germany],
)


// ── Experience ─────────────────────────────────────────────
= Experience

#cventry([2025--present], [Co-Founder of JASP Services BV])

#cventry(
  [2024--present],
  [Postdoctoral Researcher],
  subtitle: [Programme Group Psychological Methods],
  location: [University of Amsterdam, The Netherlands])

#cventry(
  [2023],
  [Postdoctoral Researcher],
  subtitle: [Department of Methodology and Statistics],
  location: [Tilburg University, The Netherlands],
)

#cventry(
  [2019--present],
  [Developer and Maintainer],
  subtitle: [#link("https://jasp-stats.org")[JASP]],
  location: [University of Amsterdam, The Netherlands],
  description: [Design, implementation, and maintenance of statistical modules],
)

#cventry(
  [2017],
  [Research Intern],
  subtitle: [Programme Group Psychological Methods],
  location: [University of Amsterdam, The Netherlands],
  description: [
    Topic: Bayesian statistics \
    Supervisor: Prof. Dr. Eric-Jan Wagenmakers
  ],
)


// ── Publications ───────────────────────────────────────────
= Publications

// Bold own name in publications
#{
  show "Pfadt, J. M.": strong
  show "Pfadt, J. M": strong

  // BEGIN GENERATED PUBLICATIONS
  cvitem([2026], [Mulder, J., & Pfadt, J. M. (2026). #emph[Going in the right direction: A tutorial to directional hypothesis testing using the BFpack module in JASP]. PsyArXiv. #link("https://doi.org/10.31234/osf.io/f582h_v3")[https://doi.org/10.31234/osf.io/f582h_v3]])
  cvitem([], [Pfadt, J. M., Merkle, E. C., & Wagenmakers, E.-J. (2026). #emph[Bayes factors for structural equation models with bridge sampling and blavaan]. PsyArXiv. #link("https://doi.org/10.31234/osf.io/pt2bc_v1")[https://doi.org/10.31234/osf.io/pt2bc_v1]])
  cvitem([], [Godmann, H. R., Molenaar, D., Ziegler, M., & Pfadt, J. M. (2026). #emph[A tutorial on assessing measurement invariance with moderated (non-)linear factor analysis in JASP]. PsyArXiv. #link("https://doi.org/10.31234/osf.io/6ftqg_v2")[https://doi.org/10.31234/osf.io/6ftqg_v2]])
  cvitem([], [Pfadt, J. M., Molenaar, D., Hurks, P., & Sijtsma, K. (2026). A tutorial on estimating the precision of individual test scores for anyone constructing and using psychological tests. #emph[Psychometrika], 1–35. #link("https://doi.org/10.1017/psy.2026.10081")[https://doi.org/10.1017/psy.2026.10081]])
  cvitem([2025], [Pfadt, J. M., Bartoš, F., Godmann, H. R., Waaijers, M., Groot, L., Heo, I., Mensink, L., Nak, J., De Ruiter, J. P., Sarafoglou, A., Siepe, B. S., Arena, G., Akrong, E., Aust, F., van den Bergh, D., Brenner, W., Doekemeijer, R. A., Donzallaz, M. C., van Doorn, J., Echevarria, N. O., . . . Wagenmakers, E.-J. (2025). #emph[A methodological metamorphosis: The rapid rise of Bayesian inference and open science practices in psychology]. PsyArXiv. #link("https://doi.org/10.31234/osf.io/ck3js_v1")[https://doi.org/10.31234/osf.io/ck3js_v1]])
  cvitem([], [Mulder, J., Pfadt, J. M., & Wagenmakers, E.-J. (2025). A tutorial on Bayesian hypothesis testing of correlation coefficients using the BFpack-module in JASP. #emph[Behavior Research Methods, 57] (11), 311. #link("https://doi.org/10.3758/s13428-025-02846-5")[https://doi.org/10.3758/s13428-025-02846-5]])
  cvitem([2023], [Pfadt, J. M., van den Bergh, D., & Moshagen, M. (2023). Classical and Bayesian uncertainty intervals for the reliability of multidimensional scales. #emph[Structural Equation Modeling: A Multidisciplinary Journal, 30] (3), 349–363. #link("https://doi.org/10.1080/10705511.2022.2124162")[https://doi.org/10.1080/10705511.2022.2124162]])
  cvitem([], [Pfadt, J. M. (2023), #emph[The present and future of reliability analyis: Advances in theory and practice] (Doctoral dissertation, Ulm University). #link("https://doi.org/10.18725/OPARU-49700")[https://doi.org/10.18725/OPARU-49700]])
  cvitem([], [Sijtsma, K., & Pfadt, J. M. (2023). Reliability. In R. Tierney, F. Rizvi, & K. Ercikan (Eds.), #emph[International encyclopedia of education] (4th ed., pp. 21-34). Elsevier. #link("https://doi.org/10.1016/B978-0-12-818630-5.10004-1")[https://doi.org/10.1016/B978-0-12-818630-5.10004-1]])
  cvitem([2022], [Pfadt, J. M., van den Bergh, D., Sijtsma, K., Moshagen, M., & Wagenmakers, E.-J. (2022). Bayesian estimation of single-test reliability coefficients. #emph[Multivariate Behavioral Research, 57] (4), 620–641. #link("https://doi.org/10.1080/00273171.2021.1891855")[https://doi.org/10.1080/00273171.2021.1891855]])
  cvitem([], [Pfadt, J. M., van den Bergh, D., Sijtsma, K., & Wagenmakers, E.-J. (2022). A tutorial on Bayesian single-test reliability analysis with JASP. #emph[Behavior Research Methods, 55] (3), 1069–1078. #link("https://doi.org/10.3758/s13428-021-01778-0")[https://doi.org/10.3758/s13428-021-01778-0]])
  cvitem([], [Pfadt, J. M., & Sijtsma, K. (2022). Statistical properties of lower bounds and factor analysis methods for reliability estimation. In #emph[Quantitative Psychology] (pp. 51–63). Springer International Publishing. #link("https://doi.org/10.1007/978-3-031-04572-1_5")[https://doi.org/10.1007/978-3-031-04572-1_5]])
  cvitem([2021], [Sijtsma, K., & Pfadt, J. M. (2021). Rejoinder: The future of reliability. #emph[Psychometrika, 86] (4), 887–892. #link("https://doi.org/10.1007/s11336-021-09807-9")[https://doi.org/10.1007/s11336-021-09807-9]])
  cvitem([], [Sijtsma, K., & Pfadt, J. M. (2021). Part II: On the use, the misuse, and the very limited usefulness of Cronbach’s alpha: Discussing lower bounds and correlated errors. #emph[Psychometrika, 86] (4), 843–860. #link("https://doi.org/10.1007/s11336-021-09789-8")[https://doi.org/10.1007/s11336-021-09789-8]])
  // END GENERATED PUBLICATIONS
}


// ── Software ───────────────────────────────────────────────
= Software

#cventry(
  [2019--present],
  [#link("https://cran.r-project.org/package=Bayesrel")[Bayesrel]],
  subtitle: [R-package],
  description: [Creator and maintainer of the R-package for Bayesian reliability estimation],
)

#cventry(
  [2020--present],
  [#link("https://jasp-stats.org")[Modules in JASP: BFpack, Factor, Reliability, SEM]],
  subtitle: [Statistics program],
  description: [Maintainer],
)


// ── Teaching ───────────────────────────────────────────────
= Teaching

#cventry(
  [2024],
  [Structural Equation Modelling],
  subtitle: [Lecturer],
  location: [Research master course],
  grade: [University of Amsterdam, The Netherlands],
)

#cventry(
  [2016--2019, 2021],
  [Applications of Multivariate Statistics in R],
  subtitle: [Instructor],
  location: [Master course],
  grade: [Ulm University, Germany],
)


// ── Talks ──────────────────────────────────────────────────
= Talks

#cventry(
  [Invited],
  [Research Section of the Forensic Psychiatry],
  subtitle: [Bayesian statistics],
  location: [Guenzburg, Germany]
)

#cventry(
  [Conference],
  [International Meeting of the Psychometric Society 2021], 
  subtitle: [Bayesian Multidimensional Reliability],
  location: [online]
)

// ── Funding, Awards & Scholarships ─────────────────────────
= Funding, Awards & Scholarships

#cvitem([2024--2026], [*Walter-Benjamin Fellowship* from the German Research Foundation (DFG) for "Bayesian Model Averaging for Structural Equation Models"])

#cvitem([2025], [*Open-Science Award* from the Open Science Community Amsterdam for "Tracking Change in Psychology: A Meta Research Project Using Human Coders and AI"])


// ── Reviewing ──────────────────────────────────────────────
= Reviewing

*Ad-hoc reviewer for*: _BMC Medical Research Methodology,
British Journal of Mathematical and Statistical Psychology,
Educational and Psychological Measurement,
European Journal of Psychological Assessment,
German Journal of Exercise and Sport Research,
Journal of Mathematical Psychology,
Psychological Methods,
Psychometrika,
Structural Equation Modeling: A Multidisciplinary Journal_
