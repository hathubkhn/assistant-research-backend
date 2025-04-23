import json
import uuid
from django.core.management.base import BaseCommand
from users.models import ResearchPaper, Dataset, DatasetReference
import random

class Command(BaseCommand):
    help = 'Import sample data for research papers and datasets from the Prisma seed file'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting data import...'))
        
        # Clear existing data
        self.stdout.write('Clearing existing data...')
        DatasetReference.objects.all().delete()
        ResearchPaper.objects.all().delete()
        Dataset.objects.all().delete()
        
        # Import sample papers
        self.stdout.write('Importing sample papers...')
        sample_papers = [
            {
                'id': str(uuid.uuid4()),
                'title': 'Attention Is All You Need',
                'authors': json.dumps(['Ashish Vaswani', 'Noam Shazeer', 'Niki Parmar', 'Jakob Uszkoreit']),
                'conference': 'NeurIPS',
                'year': 2017,
                'field': 'Artificial Intelligence',
                'keywords': json.dumps(['Transformer', 'Attention', 'NLP', 'Deep Learning']),
                'abstract': 'We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.',
                'downloadUrl': 'https://arxiv.org/pdf/1706.03762.pdf',
                'doi': '10.48550/arXiv.1706.03762',
                'bibtex': '@inproceedings{vaswani2017attention, title={Attention is all you need}, author={Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and Uszkoreit, Jakob and Jones, Llion and Gomez, Aidan N and Kaiser, {\L}ukasz and Polosukhin, Illia}, booktitle={Advances in Neural Information Processing Systems}, pages={5998--6008}, year={2017}}',
                'sourceCode': 'https://github.com/tensorflow/tensor2tensor',
                'method': 'We introduce a new architecture based entirely on attention mechanisms, allowing for much more parallelization than RNNs or CNNs.',
                'results': 'On both WMT 2014 English-to-German and WMT 2014 English-to-French translation tasks, we achieve a new state of the art. In the former task our best model outperforms even all previously reported ensembles.',
                'conclusions': 'We presented the Transformer, the first sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention.'
            },
            {
                'id': str(uuid.uuid4()),
                'title': 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
                'authors': json.dumps(['Jacob Devlin', 'Ming-Wei Chang', 'Kenton Lee', 'Kristina Toutanova']),
                'conference': 'NAACL',
                'year': 2019,
                'field': 'Computational Linguistics',
                'keywords': json.dumps(['BERT', 'Transformers', 'Pre-training', 'NLP']),
                'abstract': 'We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers.',
                'downloadUrl': 'https://arxiv.org/pdf/1810.04805.pdf',
                'doi': '10.48550/arXiv.1810.04805',
                'bibtex': '@inproceedings{devlin2019bert, title={BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding}, author={Devlin, Jacob and Chang, Ming-Wei and Lee, Kenton and Toutanova, Kristina}, booktitle={Proceedings of the 2019 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies, Volume 1 (Long and Short Papers)}, pages={4171--4186}, year={2019}}',
                'sourceCode': 'https://github.com/google-research/bert',
                'method': 'We pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers.',
                'results': 'BERT obtains new state-of-the-art results on eleven natural language processing tasks, including pushing the GLUE score to 80.5% (7.7% point absolute improvement).',
                'conclusions': 'We show that pre-trained representations eliminate the need for many heavily-engineered task-specific architectures.'
            },
            {
                'id': str(uuid.uuid4()),
                'title': 'Deep Residual Learning for Image Recognition',
                'authors': json.dumps(['Kaiming He', 'Xiangyu Zhang', 'Shaoqing Ren', 'Jian Sun']),
                'conference': 'CVPR',
                'year': 2016,
                'field': 'Computer Vision & Pattern Recognition',
                'keywords': json.dumps(['ResNet', 'CNN', 'Image Recognition', 'Deep Learning']),
                'abstract': 'Deeper neural networks are more difficult to train. We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously.',
                'downloadUrl': 'https://arxiv.org/pdf/1512.03385.pdf',
                'doi': '10.48550/arXiv.1512.03385',
                'method': 'Instead of hoping each few stacked layers directly fit a desired underlying mapping, we explicitly let these layers fit a residual mapping.',
                'results': 'On the ImageNet dataset we evaluate residual nets with a depth of up to 152 layers—8× deeper than VGG nets but still having lower complexity.',
                'conclusions': 'Deep residual nets achieve state-of-the-art accuracy with extreme depth, showing a novel degradation phenomenon when the network depth increases.'
            },
            {
                'id': str(uuid.uuid4()),
                'title': 'Generative Adversarial Networks',
                'authors': json.dumps(['Ian Goodfellow', 'Jean Pouget-Abadie', 'Mehdi Mirza', 'Bing Xu']),
                'conference': 'NIPS',
                'year': 2014,
                'field': 'Artificial Intelligence',
                'keywords': json.dumps(['GANs', 'Generative Models', 'Deep Learning']),
                'abstract': 'We propose a new framework for estimating generative models via an adversarial process, in which we simultaneously train two models: a generative model G that captures the data distribution, and a discriminative model D that estimates the probability that a sample came from the training data rather than G.',
                'downloadUrl': 'https://arxiv.org/pdf/1406.2661.pdf',
                'doi': '10.48550/arXiv.1406.2661',
                'method': 'We propose using a two-player minimax game where one network generates candidates and another evaluates them.',
                'results': 'Our method can learn to generate samples from complex distributions, including photorealistic images with coherent structure.',
                'conclusions': 'This adversarial framework offers a promising approach to generative modeling, with many potential applications.'
            },
            {
                'id': str(uuid.uuid4()),
                'title': 'A Survey of Large Language Models',
                'authors': json.dumps(['Wayne Xin Zhao', 'Kun Zhou', 'Junyi Li', 'Tianyi Tang']),
                'conference': 'ACM Computing Surveys',
                'year': 2023,
                'field': 'Computational Linguistics',
                'keywords': json.dumps(['LLM', 'Survey', 'NLP', 'Deep Learning']),
                'abstract': 'This paper presents a comprehensive survey of Large Language Models (LLMs), which have shown remarkable capabilities in various tasks and have the potential to revolutionize the way humans interact with computers.',
                'downloadUrl': 'https://arxiv.org/pdf/2303.18223.pdf',
                'doi': '10.1145/3571730',
                'bibtex': '@article{zhao2024survey, title={A Survey of Large Language Models}, author={Zhao, Wayne Xin and Zhou, Kun and Li, Junyi and Tang, Tianyi}, journal={ACM Computing Surveys}, year={2024}}',
                'sourceCode': 'https://github.com/THUDM/LLMSurvey',
                'method': 'We review the architecture, pre-training objectives, and fine-tuning methods of large language models.',
                'results': 'We identify trends and challenges in LLM research, including scaling laws, alignment, and emerging capabilities.',
                'conclusions': 'LLMs represent a significant advancement in AI and raise important questions for future research directions.'
            },
        ]
        
        # Import datasets
        self.stdout.write('Importing sample datasets...')
        datasets_seed = [
            {
                'id': 'CIFAR-100',
                'name': "CIFAR-100 (Canadian Institute for Advanced Research)",
                'abbreviation': "CIFAR-100",
                'description': "A subset of the Tiny Images dataset with 100 classes, contains 60000 32x32 color images.",
                'downloadUrl': "https://www.cs.toronto.edu/~kriz/cifar.html",
                'paperCount': 8760,
                'language': "en",
                'category': "Image",
                'tasks': json.dumps(["Image Classification", "Object Recognition"]),
                'thumbnailUrl': "/images/datasets/cifar100.jpeg",
                'benchmarks': 57
            },
            {
                'id': 'MNIST',
                'name': "Modified National Institute of Standards and Technology database",
                'abbreviation': "MNIST",
                'description': "A large collection of handwritten digits with a training set of 60,000 examples and a test set of 10,000 examples.",
                'downloadUrl': "http://yann.lecun.com/exdb/mnist/",
                'paperCount': 7511,
                'language': "en",
                'category': "Image",
                'tasks': json.dumps(["Image Classification", "Digit Recognition"]),
                'thumbnailUrl': "/images/datasets/mnist.png",
                'benchmarks': 52
            },
            {
                'id': 'NeRF',
                'name': "Neural Radiance Fields",
                'abbreviation': "NeRF",
                'description': "A method for synthesizing novel views of complex scenes by optimizing an underlying continuous volumetric scene function using a sparse set of input views.",
                'downloadUrl': "https://www.matthewtancik.com/nerf",
                'paperCount': 3635,
                'language': "en",
                'category': "3D",
                'tasks': json.dumps(["Novel View Synthesis", "3D Reconstruction"]),
                'thumbnailUrl': "/images/datasets/nerf.jpeg",
                'benchmarks': 1
            },
            {
                'id': 'KITTI',
                'name': "Karlsruhe Institute of Technology and Toyota Technological Institute",
                'abbreviation': "KITTI",
                'description': "One of the most popular datasets for use in mobile robotics and autonomous driving. It consists of hours of traffic scenarios recorded with a variety of sensor modalities.",
                'downloadUrl': "http://www.cvlibs.net/datasets/kitti/",
                'paperCount': 3586,
                'language': "en",
                'category': "Image",
                'tasks': json.dumps(["Object Detection", "Semantic Segmentation", "Depth Estimation"]),
                'thumbnailUrl': "/images/datasets/kitti.jpg",
                'benchmarks': 143
            },
            {
                'id': 'COCO',
                'name': "Common Objects in Context",
                'abbreviation': "COCO",
                'description': "A large-scale object detection, segmentation, and captioning dataset with over 200,000 labeled images.",
                'downloadUrl': "https://cocodataset.org/",
                'paperCount': 5892,
                'language': "en",
                'category': "Image",
                'tasks': json.dumps(["Object Detection", "Instance Segmentation", "Image Captioning"]),
                'thumbnailUrl': "/images/datasets/coco.jpg",
                'benchmarks': 87
            },
        ]
        
        # Create papers in database
        for paper_data in sample_papers:
            self.stdout.write(f'Creating paper: {paper_data["title"]}')
            ResearchPaper.objects.create(**paper_data)
        
        # Create datasets in database
        for dataset_data in datasets_seed:
            self.stdout.write(f'Creating dataset: {dataset_data["name"]}')
            Dataset.objects.create(**dataset_data)
        
        # Create references between papers and datasets
        papers = ResearchPaper.objects.all()
        datasets = Dataset.objects.all()
        
        self.stdout.write('Creating paper-dataset references...')
        # For each paper, assign 1-3 random datasets
        for paper in papers:
            # Shuffle datasets and pick between 1-3
            dataset_list = list(datasets)
            random.shuffle(dataset_list)
            num_datasets = random.randint(1, min(3, len(dataset_list)))
            
            for i in range(num_datasets):
                dataset = dataset_list[i]
                self.stdout.write(f'  Linking {paper.title} to {dataset.name}')
                DatasetReference.objects.create(paper=paper, dataset=dataset)
        
        self.stdout.write(self.style.SUCCESS('Sample data import completed successfully!')) 