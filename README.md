[![Documentation Status (dev)](https://readthedocs.org/projects/canflood/badge/?version=dev)](https://canflood.readthedocs.io/en/dev/)
[![Documentation Status (latest)](https://readthedocs.org/projects/canflood/badge/?version=latest)](https://canflood.readthedocs.io/en/latest/)

 
 # CanFlood
Open source flood risk modelling toolbox for Canada

![alt text](https://github.com/NRCan/CanFlood/blob/master/img/logo_20210419_500.png)


Updated and tested against QGIS 3.34.14

We welcome/encourage any comments, bugs, or issues you have or find. Please create a GitHub 'issue' ticket [following these instructions](https://github.com/NRCan/CanFlood/issues/6) to let us know about these things.

Happy flood risk modelling!


## Documentation
[Documentation](https://canflood.readthedocs.io/en/latest/#) is provided for the latest and archived versions. 


## Updates

v1.2.1 is released addressing the following:
- update to QGIS 3.34
- address issue 87: area threshold rebase
- address issue 52: Error: got negative extrapolation
- address issue 43:  Model tables are missing table numbers
- address issue 70: Rtail clarification
- address issue 93: Missing Depth-Damage Curves in IBI 2020 Dataset


[v1.2.0](https://github.com/NRCan/CanFlood/releases/tag/v1.2.0) is released with the following major new features:
1) [new tool](https://canflood.readthedocs.io/en/dev/05_toolsets.html#report-automator) for generating a pdf report of your model.

[v1.1.0](https://github.com/NRCan/CanFlood/releases/tag/v1.1.0) is released with three major new features:
1) Very nice sphinx/readTheDocs [documentation](https://canflood.readthedocs.io/en/latest/#) thanks in large part to Dhanyatha. This is much easier to browse than the previous pdfs and facilitates preservation of previous, current, and development (and eventually French) versions of the manual.
2) [new module](https://canflood.readthedocs.io/en/latest/toolsets.html#sensitivity-analysis) providing workflow and tools for performing sensitivity analysis on a L1 or L2 CanFlood models. This can be helpful in understanding and communicating the uncertainty in your model, as well as help identify which parameters should be prioritized during data collection.
3) [per-asset Sampling for Complex Geometries](https://canflood.readthedocs.io/en/latest/toolsets.html#hazard-sampler) providing more flexibility in how hazard variables are sampled from complex geometries. 

## Installation Instructions 

1) Ensure the QGIS and Qt version 'tested' above is installed and working on your system ([Qgis all releases download page](https://qgis.org/downloads/)). Ensure the 'processing' plugin is installed and enabled in QGIS.  

2) Ensure the required python packages or dependencies shown in the [requirements file](https://github.com/NRCan/CanFlood/blob/master/canflood/requirements.txt) are installed. Typically, this step is skipped and users just attempt to use the tool until an error is thrown. As of last test, a default install of QGIS 3.16 included all the CanFlood dependencies except 'openpyxl' (needed by the 'results - BCA' tools). Instructions for installing additional python packages in QGIS are provided [here](https://github.com/NRCan/CanFlood/issues/6).

3) Install the plugin from the QGIS repository (Plugins > Manage and Install... > All > search for CanFlood > Install). If a dependency error is thrown, see 'troubleshooting' below.  If successful, you should see the three CanFlood buttons on your toolbar and a 'CanFlood' entry in the 'Plugins' menu.

4) If you're re-installing or upgrading, it is safest to first uninstall CanFlood and restart QGIS before continuing with a new install.  

5) We recommend implementing the QGIS DEBUG logger for more detailed readouts and CanFlood model debugging. See [this post](https://stackoverflow.com/a/61669864/9871683) for instructions.

### tl;dr
Install from the QGIS plugin repository.  

### Troubleshooting Installation

As both QGIS and CanFlood are active open source projects, getting your installation configured can be challenging, especially if you lack admin privileges to your machine and have no pyqgis experience. Check the [issues](https://github.com/NRCan/CanFlood/issues?q=is%3Aissue) for solutions.

QGIS has retired their old installer and is no longer supporting 32-bit binaries. If you get a 'Couldn't load plugin 'canflood'' error after installing the plugin (or you have a Qt version <5.15.2), you need to install QGIS using the new standalone (msi) installers, see [this solution](https://github.com/NRCan/CanFlood/issues/27).

Some installations of QGIS may not come pre-installed with all the required python packages and dependencies listed in the [requirements](https://github.com/NRCan/CanFlood/blob/master/canflood/requirements.txt) file.  If you get a ModuleNotFound error, your QGIS install does not have the required packages. This can easily be remedied by a user with admin privileges and working pyqgis knowledge.  The following [solution](https://github.com/NRCan/CanFlood/issues/6#issuecomment-592091488) provides some guidance on installing third party python modules, but you'll likely need admin privileges. 


## Getting Started

To get started with CanFlood, we recommend reading the [documentation](https://canflood.readthedocs.io/en/latest/#) and working through the tutorials.


## I'm getting Errors!
As CanFlood is an active open-sourced project, users will often encounter errors which can be frustrating.  To work through these errors, we recommend first checking to see if there is a similar issue on the above '[issues](https://github.com/NRCan/CanFlood/issues?q=is%3Aissue)' tab.  If so, hopefully the thread will resolve the problem, if not, reply to the thread with more details on your problem and why the posted solution did not work.

If there is no issue ticket yet, follow the instructions [here](https://github.com/NRCan/CanFlood/issues/6) to post a new issue.

## CanFlood needs improvement!
We agree. Consider contacting a CanFlood developer to sponsor improvement that suites your needs, or joining the development community. Whether you'd like to integrate CanFlood modelling with some existing local databases, or integrate some other flood risk models into your analysis, or develop new output styles, the CanFlood project wants to hear from you. Please post a new issue [here](https://github.com/NRCan/CanFlood/issues/new) with an 'enhancement' label.



---

# CanFlood

Boîte à outils de modélisation des risques d’inondation libre d’accès pour le Canada

![alt text](https://github.com/NRCan/CanFlood/blob/master/img/logo_20210419_500.png)

Mis à jour et mis à l’essai par rapport à QGIS 3.22.8 (Qt 5.15.3)
Nous vous encourageons à nous faire part de vos commentaires ou à nous signaler les bogues ou problèmes que vous rencontrez. Le cas échéant, veuillez créer un billet de « problème » GitHub [en suivant ces instructions](https://github.com/NRCan/CanFlood/issues/6) pour nous en faire part.

Bonne modélisation de risques d’inondation!

## Documentation

De la [documentation](https://canflood.readthedocs.io/fr/latest/) est fournie pour la plus récente version et les versions archivées.

## Phase 3 – Élaboration

La v1.2.0 est publiée avec les nouvelles fonctionnalités majeures suivantes:
1)	Nouvel outil pour générer un rapport de votre modèle en format PDF.

La v1.1.0 comprend les trois nouvelles fonctionnalités majeures suivantes:
1) Très bonne documentation sur Sphinx et Read the Docs, créée en grande partie par Dhanyatha. Cette version est beaucoup plus facile à consulter que les précédents fichiers en format PDF, et elle facilite la conservation des versions précédentes, actuelles et en développement (et ultimement en français) du manuel.
2) Nouveau module fournissant un flux de travail et des outils pour effectuer une analyse de sensibilité sur un modèle CanFlood L1 ou L2. Il peut être utile pour comprendre et communiquer l’incertitude subsistant dans votre modèle, ainsi que pour déterminer les paramètres auxquels accorder la priorité lors de la collecte des données.
3) Échantillonnage par actif pour les géométries complexes offrant plus de souplesse dans la façon dont les variables de risque sont échantillonnées à partir de géométries complexes.

## Instructions d’installation

1) Assurez-vous que les versions de QGIS et de Qt ci-dessus mises à l’essai ci-dessus sont installées et fonctionnent sur votre système (Page de téléchargement de toutes les versions de QGIS). Assurez-vous que le plugiciel de traitement (« processing ») est installé et activé dans QGIS.

2) Assurez-vous que les modules Python requis et les dépendances indiquées dans le fichier des exigences sont installés. Normalement, cette étape est ignorée et les utilisateurs tentent simplement d’utiliser l’outil jusqu’à ce qu’une erreur se produise. En date du dernier essai, une installation par défaut de QGIS 3.16 incluait toutes les dépendances de CanFlood à l’exception de « openpyxl » (nécessaire pour les outils « résultats – ACC »). Des instructions pour l’installation de modules Python supplémentaires dans QGIS sont fournies ici.

3) Installez le plugiciel à partir du référentiel QGIS (Plugins > Manage and Install... > All > recherchez CanFlood > Install). Si une erreur de dépendance se produit, consultez la section « Dépannage » ci-dessous. Si vous avez réussi, vous devriez voir les trois boutons de CanFlood sur votre barre d’outils et une entrée « CanFlood » dans le menu « Plugins ».

4) Si vous effectuez une réinstallation ou une mise à niveau, il est plus sûr de désinstaller CanFlood et de redémarrer QGIS avant de procéder à une nouvelle installation.

5) Nous recommandons d’utiliser l’enregistreur chronologique QGIS DEBUG pour des lectures plus détaillées et le débogage de modèles CanFlood. Voir cette publication pour les instructions.

### tl;pl
Lancez l’installation à partir du référentiel de plugiciels QGIS.

### Dépannage de l’installation

Comme QGIS et CanFlood sont tous deux des projets actifs à code source ouvert, la configuration de votre installation peut s’avérer difficile, surtout si vous ne disposez pas des privilèges d’administrateur sur votre appareil et que vous n’avez aucune expérience avec pyqgis. Consultez les problèmes pour trouver des solutions.

QGIS a retiré son ancien installateur et ne prend plus en charge les binaires 32 bits. Si vous obtenez une erreur « Couldn’t load plugiciel canflood » après avoir installé le plugiciel (ou si vous avez une version de Qt antérieure à la version 5.15.2), vous devez installer QGIS en utilisant les nouveaux installateurs (msi) autonomes. Référez-vous à cette solution.

Certaines installations de QGIS peuvent ne pas être préinstallées avec tous les modules Python requis et les dépendances répertoriées dans le fichier des exigences. Si vous obtenez une erreur ModuleNotFound, votre installation de QGIS ne dispose pas des modules requis. Ceci peut être facilement corrigé par un utilisateur ayant des privilèges d’administrateur et une connaissance pratique de pyqgis. La solution suivante fournit quelques conseils sur l’installation de modules Python tiers, mais vous aurez probablement besoin de privilèges d’administrateur.

## Pour commencer

Pour commencer à utiliser CanFlood, nous vous recommandons de lire la documentation et de suivre les tutoriels.

## J’obtiens des messages d’erreur!

Comme CanFlood est un projet actif à code source ouvert, les utilisateurs rencontreront souvent des erreurs qui pourraient s’avérer frustrantes. Pour résoudre ces erreurs, nous vous recommandons de vérifier d’abord s’il existe un problème comparable dans l’onglet des problèmes ci-dessus. Si c’est le cas, nous espérons que le fil de discussion vous aidera à le résoudre. Sinon, répondez au fil de discussion en donnant plus de détails sur votre problème et en expliquant pourquoi la solution affichée n’a pas fonctionné.
S’il n’y a pas encore de billet de problème, suivez les instructions ici pour publier un nouveau problème.

## CanFlood doit être amélioré!

Nous sommes du même avis. Envisagez de communiquer avec un développeur de CanFlood pour lui faire part d’une amélioration qui répondrait à vos besoins, ou de devenir membre de la communauté de développement. Que vous souhaitiez intégrer la modélisation de CanFlood à certaines bases de données locales existantes, intégrer d’autres modèles de risques d’inondation dans votre analyse, ou encore mettre au point de nouveaux styles d’extrants, l’équipe du projet CanFlood souhaite vous entendre. Veuillez publier un nouveau problème ici avec l’étiquette « amélioration ».



