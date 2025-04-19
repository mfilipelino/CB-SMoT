# CB-SMoT

## Overview
CB-SMoT (Clustering-Based Stops and Moves of Trajectories) is an algorithm for discovering interesting places in trajectories based on the variation of speed. The algorithm identifies stops (places where an object stayed for a relevant amount of time) and moves (segments between stops) in a trajectory.

This implementation focuses on identifying congestion regions in public transportation in São Paulo city using the Olho Vivo API.

## Algorithm Description
The CB-SMoT algorithm works by:
1. Analyzing the speed variation in a trajectory
2. Identifying segments where the speed is lower than a threshold for a minimum amount of time
3. Classifying these segments as potential stops
4. Associating these stops with semantic information (e.g., bus stops, traffic congestion areas)

## Academic References
The CB-SMoT algorithm was proposed in the following papers:

1. Palma, A. T., Bogorny, V., Kuijpers, B., & Alvares, L. O. (2008). "A clustering-based approach for discovering interesting places in trajectories." In Proceedings of the 2008 ACM symposium on Applied computing (pp. 863-868).

2. Alvares, L. O., Bogorny, V., Kuijpers, B., de Macedo, J. A. F., Moelans, B., & Vaisman, A. (2007). "A model for enriching trajectories with semantic geographical information." In Proceedings of the 15th annual ACM international symposium on Advances in geographic information systems (pp. 1-8).

## Project Documentation
This project implements the CB-SMoT algorithm in a Django application to analyze public transportation data from São Paulo city.

### Presentation
Slides (in Portuguese): [Identificação semântica de regiões de congestionamento no transporte público da cidade de São Paulo, utilizando API Olho Vivo](https://drive.google.com/open?id=108H7DcA4e-1lTS9Nd5uoH5anfThruVe14oZFPv1kka0)

## Testing
The project includes comprehensive unit tests for:
- Core algorithm functions (haversine distance, speed calculations)
- Stop detection logic
- Service functions for data management

Run the tests with:
```bash
# Run algorithm tests (no Django dependencies)
python test_cbsmot_algorithm.py

# Run Django-based tests
cd geodjango
python manage.py test core.test_service_functions
python manage.py test core.test_utils
```
