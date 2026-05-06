\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{aliusbulletin}[2026/04/22 ALIUS Bulletin reconstruction template]

\LoadClass[11pt]{article}

\RequirePackage[a4paper,left=31.75mm,right=31.75mm,top=25.40mm,bottom=28.50mm,headheight=34pt,headsep=10pt,footskip=18pt]{geometry}
\RequirePackage{calc}
\RequirePackage{etoolbox}
\RequirePackage{fancyhdr}
\RequirePackage{fontspec}
\RequirePackage{graphicx}
\RequirePackage{xcolor}
\RequirePackage{hyperref}
\RequirePackage{microtype}
\RequirePackage{ragged2e}
\RequirePackage{setspace}
\RequirePackage{xparse}

\hypersetup{
  colorlinks=true,
  linkcolor=black,
  urlcolor=black,
  citecolor=black,
  pdfauthor={ALIUS},
  pdftitle={ALIUS Bulletin}
}

\defaultfontfeatures{Ligatures=TeX,Scale=MatchLowercase}
\setmainfont[
  Path=assets/fonts/,
  UprightFont=CormorantGaramond-Regular.ttf,
  ItalicFont=CormorantGaramond-Italic.ttf,
  BoldFont=CormorantGaramond-Bold.ttf,
  BoldItalicFont=CormorantGaramond-BoldItalic.ttf
]{Cormorant Garamond}

\newfontfamily\AliusLato[
  Path=assets/fonts/,
  UprightFont=Lato-Regular.ttf,
  ItalicFont=Lato-Italic.ttf,
  BoldFont=Lato-Bold.ttf,
  BoldItalicFont=Lato-BoldItalic.ttf
]{Lato}

\newfontfamily\AliusLatoLight[
  Path=assets/fonts/,
  UprightFont=Lato-Light.ttf,
  ItalicFont=Lato-LightItalic.ttf,
  BoldFont=Lato-Regular.ttf,
  BoldItalicFont=Lato-Italic.ttf
]{Lato}

\newfontfamily\AliusCormorantLight[
  Path=assets/fonts/,
  UprightFont=CormorantGaramond-Light.ttf,
  ItalicFont=CormorantGaramond-LightItalic.ttf,
  BoldFont=CormorantGaramond-Regular.ttf,
  BoldItalicFont=CormorantGaramond-Italic.ttf
]{Cormorant Garamond}

\microtypesetup{protrusion=true,expansion=true}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\raggedbottom

\definecolor{AliusGreen}{HTML}{1F8135}
\definecolor{AliusBody}{HTML}{515151}
\color{AliusBody}

\makeatletter

\newif\ifAliusBundleMode
\AliusBundleModefalse

\def\AliusIssueNumber{}
\def\AliusYear{}
\def\AliusPieceSlug{}
\def\AliusPieceType{}
\def\AliusTitle{}
\def\AliusSubtitle{}
\def\AliusCreditLine{}
\def\AliusRunningTitle{}
\def\AliusCitationLabel{Cite as:}
\def\AliusStandaloneCitation{}
\def\AliusBundleCitation{}
\def\AliusAbstract{}
\def\AliusKeywordsLabel{Keywords:}
\def\AliusKeywords{}
\def\AliusContributors{}
\def\AliusTitleSize{20}
\def\AliusTitleLeading{24}
\def\AliusSubtitleSize{20}
\def\AliusSubtitleLeading{24}
\def\AliusCreditSize{13}
\def\AliusCreditLeading{15}
\def\AliusFooterPrefix{ALIUS Bulletin}
\def\AliusFooterUrl{aliusresearch.org/bulletin}

\newcommand{\AliusEnableBundleMode}{\AliusBundleModetrue}
\newcommand{\AliusDisableBundleMode}{\AliusBundleModefalse}

\newcommand{\AliusSetIssueNumber}[1]{\gdef\AliusIssueNumber{#1}}
\newcommand{\AliusSetYear}[1]{\gdef\AliusYear{#1}}
\newcommand{\AliusSetPieceSlug}[1]{\gdef\AliusPieceSlug{#1}}
\newcommand{\AliusSetPieceType}[1]{\gdef\AliusPieceType{#1}}
\newcommand{\AliusSetTitle}[1]{\gdef\AliusTitle{#1}}
\newcommand{\AliusSetSubtitle}[1]{\gdef\AliusSubtitle{#1}}
\newcommand{\AliusSetCreditLine}[1]{\gdef\AliusCreditLine{#1}}
\newcommand{\AliusSetRunningTitle}[1]{\gdef\AliusRunningTitle{#1}}
\newcommand{\AliusSetCitationLabel}[1]{\gdef\AliusCitationLabel{#1}}
\newcommand{\AliusSetStandaloneCitation}[1]{\gdef\AliusStandaloneCitation{#1}}
\newcommand{\AliusSetBundleCitation}[1]{\gdef\AliusBundleCitation{#1}}
\newcommand{\AliusSetAbstract}[1]{\gdef\AliusAbstract{#1}}
\newcommand{\AliusSetKeywordsLabel}[1]{\gdef\AliusKeywordsLabel{#1}}
\newcommand{\AliusSetKeywords}[1]{\gdef\AliusKeywords{#1}}
\newcommand{\AliusSetTitleSize}[2]{\gdef\AliusTitleSize{#1}\gdef\AliusTitleLeading{#2}}
\newcommand{\AliusSetSubtitleSize}[2]{\gdef\AliusSubtitleSize{#1}\gdef\AliusSubtitleLeading{#2}}
\newcommand{\AliusSetCreditSize}[2]{\gdef\AliusCreditSize{#1}\gdef\AliusCreditLeading{#2}}
\newcommand{\AliusSetFooterPrefix}[1]{\gdef\AliusFooterPrefix{#1}}
\newcommand{\AliusSetFooterUrl}[1]{\gdef\AliusFooterUrl{#1}}
\newcommand{\AliusClearContributors}{\gdef\AliusContributors{}}
\newcommand{\AliusAddContributor}[2]{%
  \gappto\AliusContributors{%
    {\AliusLato\fontsize{11}{13}\selectfont #1\par}%
    {\AliusLatoLight\fontsize{9}{11}\selectfont #2\par}%
    \vspace{0.9em}%
  }%
}

\newcommand{\AliusCurrentCitation}{%
  \ifAliusBundleMode
    \ifx\AliusBundleCitation\@empty
      \AliusStandaloneCitation
    \else
      \AliusBundleCitation
    \fi
  \else
    \AliusStandaloneCitation
  \fi
}

\newcommand{\AliusFooterText}{%
  \AliusFooterPrefix\ n\textdegree\ \AliusIssueNumber\ (\AliusYear)\hfill \AliusFooterUrl%
}

\newcommand{\AliusHeaderTitle}{%
  \ifx\AliusRunningTitle\@empty
    \AliusTitle
  \else
    \AliusRunningTitle
  \fi
}

\fancypagestyle{aliuspiece}{%
  \fancyhf{}%
  \fancyhead[C]{%
    \begin{tabular}{c}
      {\AliusCormorantLight\fontsize{14}{15}\selectfont \AliusHeaderTitle}\\[-1pt]
      {\AliusCormorantLight\fontsize{12}{12}\selectfont \thepage}
    \end{tabular}%
  }%
  \fancyfoot[C]{%
    {\AliusCormorantLight\fontsize{12}{12}\selectfont \AliusFooterText}%
  }%
  \renewcommand{\headrulewidth}{0pt}%
  \renewcommand{\footrulewidth}{0pt}%
}

\fancypagestyle{aliusfirstpage}{%
  \fancyhf{}%
  \fancyfoot[C]{%
    {\AliusCormorantLight\fontsize{12}{12}\selectfont \AliusFooterText}%
  }%
  \renewcommand{\headrulewidth}{0pt}%
  \renewcommand{\footrulewidth}{0pt}%
}

\pagestyle{aliuspiece}

\newcommand{\AliusRenderContributors}{%
  \begingroup
  \RaggedRight
  \AliusContributors
  \endgroup
}

\newcommand{\AliusRenderFrontMatter}{%
  \thispagestyle{aliusfirstpage}%
  {\AliusLato\fontsize{\AliusTitleSize}{\AliusTitleLeading}\selectfont \AliusTitle\par}%
  \ifx\AliusSubtitle\@empty\else
    \vspace{0.8em}%
    {\AliusLatoLight\fontsize{\AliusSubtitleSize}{\AliusSubtitleLeading}\selectfont \AliusSubtitle\par}%
  \fi
  \ifx\AliusCreditLine\@empty\else
    \vspace{1.1em}%
    {\AliusLatoLight\fontsize{\AliusCreditSize}{\AliusCreditLeading}\selectfont \AliusCreditLine\par}%
  \fi
  \vspace{1.1em}%
  \begin{minipage}[t]{0.64\textwidth}
    {\AliusLatoLight\fontsize{10}{12.5}\selectfont \AliusCitationLabel\ \AliusCurrentCitation\par}%
  \end{minipage}\hfill
  \begin{minipage}[t]{0.28\textwidth}
    \AliusRenderContributors
  \end{minipage}%
  \vspace{1.3em}%
  {\AliusLato\fontsize{14}{16}\selectfont Abstract\par}%
  \vspace{0.55em}%
  {\AliusLatoLight\fontsize{12}{15}\selectfont \AliusAbstract\par}%
  \ifx\AliusKeywords\@empty\else
    \vspace{1em}%
    {\AliusLatoLight\fontsize{12}{14}\selectfont \textit{\AliusKeywordsLabel}\ \textit{\AliusKeywords}\par}%
  \fi
  \vspace{1.3em}%
}

\newcommand{\AliusStartPiece}{%
  \clearpage
  \label{\AliusPieceSlug:start}%
  \AliusRenderFrontMatter
  \pagestyle{aliuspiece}%
}

\newcommand{\AliusStartPieceHere}{%
  \label{\AliusPieceSlug:start}%
  \AliusRenderFrontMatter
  \pagestyle{aliuspiece}%
}

\newcommand{\AliusFinishPiece}{%
  \par
  \label{\AliusPieceSlug:end}%
}

\NewDocumentCommand{\AliusQuestion}{m}{%
  \vspace{1.05em}%
  {\AliusLato\fontsize{12.4}{14.8}\selectfont #1\par}%
}

\NewDocumentCommand{\AliusAnswer}{m}{%
  \vspace{0.72em}%
  {\fontsize{14}{16.4}\selectfont #1\par}%
}

\NewDocumentCommand{\AliusSpeakerAnswer}{m m}{%
  \vspace{0.72em}%
  {\fontsize{14}{16.4}\selectfont \textbf{#1}\ #2\par}%
}

\NewDocumentCommand{\AliusParagraph}{m}{%
  \vspace{0.72em}%
  {\fontsize{14}{16.4}\selectfont #1\par}%
}

\NewDocumentCommand{\AliusSectionHeading}{m}{%
  \vspace{1.4em}%
  {\AliusLato\fontsize{14}{16}\selectfont #1\par}%
  \vspace{0.4em}%
}

\NewDocumentCommand{\AliusReferenceEntry}{m}{%
  \vspace{0.35em}%
  {\fontsize{13}{15.2}\selectfont \hangindent=1.4em \hangafter=1 #1\par}%
}

\NewDocumentCommand{\AliusPullQuote}{m}{%
  \vspace{1.25em}%
  \begin{center}
    \makebox[0pt][l]{\hspace*{-1.0em}{\AliusCormorantLight\fontsize{48}{36}\selectfont ``}}%
    \begin{minipage}{0.76\linewidth}
      \centering
      {\AliusLatoLight\fontsize{15}{18}\selectfont #1\par}%
    \end{minipage}%
    \makebox[0pt][r]{{\AliusCormorantLight\fontsize{48}{36}\selectfont ''}}%
  \end{center}
  \vspace{0.8em}%
}

\NewDocumentCommand{\AliusIssueCoverPage}{m}{%
  \clearpage
  \thispagestyle{empty}%
  \noindent\includegraphics[width=\paperwidth,height=\paperheight]{#1}%
  \clearpage
}

\NewDocumentCommand{\AliusIssueBlankPage}{}{%
  \clearpage
  \thispagestyle{empty}%
  \null
  \clearpage
}

\NewDocumentCommand{\AliusIssueCenteredTitle}{m}{%
  \clearpage
  \thispagestyle{empty}%
  \vspace*{2.4cm}%
  \begin{center}
    {\AliusLato\fontsize{22}{28}\selectfont #1\par}
  \end{center}
  \vspace{1.5cm}%
}

\NewDocumentCommand{\AliusIssueTOCEntry}{m m m m}{%
  {\AliusLatoLight\fontsize{12}{15}\selectfont \textbf{#2}\ #3\par}%
  {\AliusLatoLight\fontsize{12}{15}\selectfont #4\dotfill \pageref*{#1:start}\par}%
  \vspace{0.9em}%
}

\makeatother
