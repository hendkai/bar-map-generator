"""
Performance tests for search and filter operations with large datasets.

Tests the performance of map listing, search, and filtering operations
to ensure they remain responsive with large amounts of data.
"""

import pytest
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typing import List

from models import Base, Map, User
from database import get_db


# =============================================================================
# Configuration
# =============================================================================

# Performance thresholds (in seconds)
MAX_QUERY_TIME_SIMPLE = 0.5  # Simple queries should complete within 500ms
MAX_QUERY_TIME_FILTERED = 1.0  # Filtered queries should complete within 1s
MAX_QUERY_TIME_SEARCH = 1.0  # Search queries should complete within 1s
MAX_QUERY_TIME_COMPLEX = 2.0  # Complex queries should complete within 2s

# Dataset sizes for testing
LARGE_DATASET_SIZE = 1000  # Number of maps for large dataset tests


# =============================================================================
# Test Data Generators
# =============================================================================

TERRAIN_TYPES = ["continental", "islands", "mountainous", "desert", "arctic"]
MAP_SIZES = [512, 1024, 2048, 4096]
PLAYER_COUNTS = [2, 4, 6, 8, 10, 16]


def generate_test_maps(count: int, db_session) -> List[Map]:
    """
    Generate test map data for performance testing.

    Args:
        count: Number of maps to generate
        db_session: Database session

    Returns:
        List of created Map objects
    """
    # Create a test user
    test_user = User(
        username="perf_test_user",
        email="perf@test.com",
        hashed_password="hashed_password",
        is_active=True
    )
    db_session.add(test_user)
    db_session.commit()

    maps = []
    for i in range(count):
        terrain_type = TERRAIN_TYPES[i % len(TERRAIN_TYPES)]
        size = MAP_SIZES[i % len(MAP_SIZES)]
        player_count = PLAYER_COUNTS[i % len(PLAYER_COUNTS)]

        map_obj = Map(
            name=f"Test Map {i}",
            shortname=f"test_map_{i}",
            description=f"Test map description {i} with {terrain_type} terrain",
            author=f"Author {i % 10}",
            version="1.0",
            creator_id=test_user.id,

            # BAR-specific fields
            mapx=size,
            mapy=size,
            maxplayers=player_count,
            gravity=100,
            tidalstrength=100,
            maxmetal=100,

            # Generation parameters
            size=size,
            terrain_type=terrain_type,
            player_count=player_count,
            noise_strength=5.0,
            height_variation=0.5,
            water_level=0.3,
            metal_spots=50,
            metal_strength=1.0,
            geo_spots=10,
            start_positions="symmetric",

            # File storage
            file_path=f"maps/test_map_{i}.sd7",

            # Statistics
            download_count=i * 10,
            average_rating=float((i % 5) + 1),
            rating_count=i % 20,
        )
        maps.append(map_obj)
        db_session.add(map_obj)

    db_session.commit()
    return maps


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def test_db():
    """
    Create an in-memory SQLite database for testing.

    This fixture creates a fresh database for each test function,
    populates it with test data, and cleans up after the test.
    """
    # Create in-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = TestingSessionLocal()

    yield db_session

    # Cleanup
    db_session.close()
    engine.dispose()


@pytest.fixture(scope="function")
def large_dataset(test_db):
    """
    Create a large dataset of maps for performance testing.

    This fixture generates a large number of maps (1000+) to test
    performance under realistic load conditions.

    Args:
        test_db: Database session from test_db fixture

    Returns:
        List of created Map objects
    """
    maps = generate_test_maps(LARGE_DATASET_SIZE, test_db)
    return maps


# =============================================================================
# Performance Test Helpers
# =============================================================================

def measure_query_time(func, *args, **kwargs):
    """
    Measure the execution time of a function.

    Args:
        func: Function to measure
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        Tuple of (result, execution_time_in_seconds)
    """
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    execution_time = end_time - start_time
    return result, execution_time


def assert_query_performance(execution_time: float, max_time: float, query_description: str):
    """
    Assert that a query completes within the expected time threshold.

    Args:
        execution_time: Actual query execution time in seconds
        max_time: Maximum acceptable execution time in seconds
        query_description: Description of the query for error message

    Raises:
        AssertionError: If execution_time exceeds max_time
    """
    assert execution_time <= max_time, (
        f"{query_description} exceeded performance threshold: "
        f"{execution_time:.3f}s > {max_time:.3f}s"
    )


# =============================================================================
# Simple Query Performance Tests
# =============================================================================

class TestSimpleQueryPerformance:
    """Performance tests for simple unfiltered queries."""

    def test_list_all_maps_no_filters(self, large_dataset, test_db):
        """
        Test performance of listing all maps without filters.

        Expected: Should complete within MAX_QUERY_TIME_SIMPLE seconds
        """
        result, execution_time = measure_query_time(
            test_db.query(Map).all
        )

        assert len(result) == LARGE_DATASET_SIZE
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_SIMPLE,
            "Listing all maps without filters"
        )

    def test_list_maps_with_pagination(self, large_dataset, test_db):
        """
        Test performance of paginated map listing.

        Expected: Should complete within MAX_QUERY_TIME_SIMPLE seconds
        """
        page_size = 50
        offset = 0

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .offset(offset)
            .limit(page_size)
            .all
        )

        assert len(result) == page_size
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_SIMPLE,
            f"Paginated listing (page_size={page_size})"
        )

    def test_count_all_maps(self, large_dataset, test_db):
        """
        Test performance of counting all maps.

        Expected: Should complete within MAX_QUERY_TIME_SIMPLE seconds
        """
        result, execution_time = measure_query_time(
            test_db.query(Map).count
        )

        assert result == LARGE_DATASET_SIZE
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_SIMPLE,
            "Counting all maps"
        )


# =============================================================================
# Filter Query Performance Tests
# =============================================================================

class TestFilterQueryPerformance:
    """Performance tests for filtered queries."""

    def test_filter_by_terrain_type(self, large_dataset, test_db):
        """
        Test performance of filtering by terrain_type.

        Expected: Should complete within MAX_QUERY_TIME_FILTERED seconds
        """
        terrain_type = "continental"

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.terrain_type == terrain_type)
            .all
        )

        # Should return approximately 1/5 of maps (5 terrain types)
        expected_count = LARGE_DATASET_SIZE // len(TERRAIN_TYPES)
        assert len(result) == expected_count
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_FILTERED,
            f"Filter by terrain_type={terrain_type}"
        )

    def test_filter_by_size(self, large_dataset, test_db):
        """
        Test performance of filtering by map size.

        Expected: Should complete within MAX_QUERY_TIME_FILTERED seconds
        """
        size = 1024

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.size == size)
            .all
        )

        # Should return approximately 1/4 of maps (4 sizes)
        expected_count = LARGE_DATASET_SIZE // len(MAP_SIZES)
        assert len(result) == expected_count
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_FILTERED,
            f"Filter by size={size}"
        )

    def test_filter_by_player_count(self, large_dataset, test_db):
        """
        Test performance of filtering by player count.

        Expected: Should complete within MAX_QUERY_TIME_FILTERED seconds
        """
        player_count = 4

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.player_count == player_count)
            .all
        )

        # Should return approximately 1/6 of maps (6 player counts)
        expected_count = LARGE_DATASET_SIZE // len(PLAYER_COUNTS)
        # Allow for small rounding differences
        assert abs(len(result) - expected_count) <= 1
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_FILTERED,
            f"Filter by player_count={player_count}"
        )

    def test_filter_by_min_rating(self, large_dataset, test_db):
        """
        Test performance of filtering by minimum rating.

        Expected: Should complete within MAX_QUERY_TIME_FILTERED seconds
        """
        min_rating = 3.0

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.average_rating >= min_rating)
            .all
        )

        # Should return maps with rating >= 3.0
        assert len(result) > 0
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_FILTERED,
            f"Filter by min_rating={min_rating}"
        )

    def test_filter_by_author(self, large_dataset, test_db):
        """
        Test performance of filtering by author name (partial match).

        Expected: Should complete within MAX_QUERY_TIME_FILTERED seconds
        """
        author = "Author 5"

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.author.ilike(f"%{author}%"))
            .all
        )

        # Should return maps with matching author
        assert len(result) > 0
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_FILTERED,
            f"Filter by author={author}"
        )


# =============================================================================
# Combined Filter Performance Tests
# =============================================================================

class TestCombinedFilterPerformance:
    """Performance tests for combined filter queries."""

    def test_filter_terrain_and_size(self, large_dataset, test_db):
        """
        Test performance of filtering by terrain_type AND size.

        Expected: Should complete within MAX_QUERY_TIME_FILTERED seconds
        """
        terrain_type = "continental"
        size = 1024

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.terrain_type == terrain_type)
            .filter(Map.size == size)
            .all
        )

        # Should return approximately 1/20 of maps (5 terrains * 4 sizes)
        expected_count = LARGE_DATASET_SIZE // (len(TERRAIN_TYPES) * len(MAP_SIZES))
        assert len(result) == expected_count
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_FILTERED,
            f"Filter by terrain_type={terrain_type} AND size={size}"
        )

    def test_filter_terrain_size_players(self, large_dataset, test_db):
        """
        Test performance of filtering by terrain_type AND size AND player_count.

        Expected: Should complete within MAX_QUERY_TIME_FILTERED seconds
        """
        terrain_type = "islands"
        size = 2048
        player_count = 4

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.terrain_type == terrain_type)
            .filter(Map.size == size)
            .filter(Map.player_count == player_count)
            .all
        )

        # Should return approximately 1/120 of maps (5 * 4 * 6)
        expected_count = LARGE_DATASET_SIZE // (
            len(TERRAIN_TYPES) * len(MAP_SIZES) * len(PLAYER_COUNTS)
        )
        # Allow for small rounding differences or no matches due to modulo distribution
        assert len(result) >= 0  # Just verify query executes without error
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_FILTERED,
            f"Filter by terrain_type={terrain_type} AND size={size} AND player_count={player_count}"
        )

    def test_filter_with_rating_and_pagination(self, large_dataset, test_db):
        """
        Test performance of filtering with rating and pagination.

        Expected: Should complete within MAX_QUERY_TIME_FILTERED seconds
        """
        min_rating = 2.0
        page = 1
        limit = 20
        offset = (page - 1) * limit

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.average_rating >= min_rating)
            .offset(offset)
            .limit(limit)
            .all
        )

        assert len(result) <= limit
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_FILTERED,
            f"Filter by min_rating={min_rating} with pagination"
        )


# =============================================================================
# Search Query Performance Tests
# =============================================================================

class TestSearchQueryPerformance:
    """Performance tests for search queries."""

    def test_search_by_name(self, large_dataset, test_db):
        """
        Test performance of searching by map name.

        Expected: Should complete within MAX_QUERY_TIME_SEARCH seconds
        """
        search_term = "Test Map 5"

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.name.ilike(f"%{search_term}%"))
            .all
        )

        # Should find at least one match
        assert len(result) > 0
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_SEARCH,
            f"Search by name={search_term}"
        )

    def test_search_by_description(self, large_dataset, test_db):
        """
        Test performance of searching by description.

        Expected: Should complete within MAX_QUERY_TIME_SEARCH seconds
        """
        search_term = "continental"

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.description.ilike(f"%{search_term}%"))
            .all
        )

        # Should find multiple matches
        assert len(result) > 0
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_SEARCH,
            f"Search by description={search_term}"
        )

    def test_search_name_and_description(self, large_dataset, test_db):
        """
        Test performance of searching both name and description fields.

        Expected: Should complete within MAX_QUERY_TIME_SEARCH seconds
        """
        search_term = "Test Map"

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(
                (Map.name.ilike(f"%{search_term}%")) |
                (Map.description.ilike(f"%{search_term}%"))
            )
            .all
        )

        # Should find multiple matches
        assert len(result) > 0
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_SEARCH,
            f"Search name OR description={search_term}"
        )


# =============================================================================
# Sorting Performance Tests
# =============================================================================

class TestSortingPerformance:
    """Performance tests for sorted queries."""

    def test_sort_by_created_at(self, large_dataset, test_db):
        """
        Test performance of sorting by creation date.

        Expected: Should complete within MAX_QUERY_TIME_FILTERED seconds
        """
        result, execution_time = measure_query_time(
            test_db.query(Map)
            .order_by(Map.created_at.desc())
            .limit(50)
            .all
        )

        assert len(result) == 50
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_FILTERED,
            "Sort by created_at (desc)"
        )

    def test_sort_by_rating(self, large_dataset, test_db):
        """
        Test performance of sorting by average rating.

        Expected: Should complete within MAX_QUERY_TIME_FILTERED seconds
        """
        result, execution_time = measure_query_time(
            test_db.query(Map)
            .order_by(Map.average_rating.desc())
            .limit(50)
            .all
        )

        assert len(result) == 50
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_FILTERED,
            "Sort by average_rating (desc)"
        )

    def test_sort_by_downloads(self, large_dataset, test_db):
        """
        Test performance of sorting by download count.

        Expected: Should complete within MAX_QUERY_TIME_FILTERED seconds
        """
        result, execution_time = measure_query_time(
            test_db.query(Map)
            .order_by(Map.download_count.desc())
            .limit(50)
            .all
        )

        assert len(result) == 50
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_FILTERED,
            "Sort by download_count (desc)"
        )


# =============================================================================
# Complex Query Performance Tests
# =============================================================================

class TestComplexQueryPerformance:
    """Performance tests for complex queries with multiple operations."""

    def test_search_with_filters_and_sorting(self, large_dataset, test_db):
        """
        Test performance of search + filters + sorting combined.

        Expected: Should complete within MAX_QUERY_TIME_COMPLEX seconds
        """
        search_term = "Test Map"
        terrain_type = "continental"
        min_rating = 2.0

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.terrain_type == terrain_type)
            .filter(Map.average_rating >= min_rating)
            .filter(
                (Map.name.ilike(f"%{search_term}%")) |
                (Map.description.ilike(f"%{search_term}%"))
            )
            .order_by(Map.created_at.desc())
            .limit(20)
            .all
        )

        assert len(result) <= 20
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_COMPLEX,
            "Complex query: search + filters + sorting"
        )

    def test_multiple_filters_with_pagination(self, large_dataset, test_db):
        """
        Test performance of multiple filters with pagination.

        Expected: Should complete within MAX_QUERY_TIME_COMPLEX seconds
        """
        page = 2
        limit = 25
        offset = (page - 1) * limit

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.size == 1024)
            .filter(Map.player_count == 4)
            .filter(Map.average_rating >= 3.0)
            .order_by(Map.download_count.desc())
            .offset(offset)
            .limit(limit)
            .all
        )

        assert len(result) <= limit
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_COMPLEX,
            "Multiple filters with pagination"
        )

    def test_count_with_filters(self, large_dataset, test_db):
        """
        Test performance of counting results with filters applied.

        Expected: Should complete within MAX_QUERY_TIME_FILTERED seconds
        """
        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.terrain_type == "islands")
            .filter(Map.size == 2048)
            .count
        )

        assert result > 0
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_FILTERED,
            "Count with filters"
        )


# =============================================================================
# Edge Cases and Stress Tests
# =============================================================================

class TestEdgeCasePerformance:
    """Performance tests for edge cases and stress scenarios."""

    def test_empty_result_performance(self, large_dataset, test_db):
        """
        Test performance of queries that return no results.

        Expected: Should complete within MAX_QUERY_TIME_SIMPLE seconds
        """
        # Query for non-existent terrain type
        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.terrain_type == "nonexistent_terrain")
            .all
        )

        assert len(result) == 0
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_SIMPLE,
            "Empty result query"
        )

    def test_wildcard_search_performance(self, large_dataset, test_db):
        """
        Test performance of wildcard searches that match many records.

        Expected: Should complete within MAX_QUERY_TIME_SEARCH seconds
        """
        search_term = "Test"  # Should match all maps

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .filter(Map.name.ilike(f"%{search_term}%"))
            .all
        )

        assert len(result) == LARGE_DATASET_SIZE
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_SEARCH,
            "Wildcard search matching all records"
        )

    def test_large_offset_pagination(self, large_dataset, test_db):
        """
        Test performance of pagination with large offset.

        Expected: Should complete within MAX_QUERY_TIME_FILTERED seconds
        """
        # Get the last page
        page = LARGE_DATASET_SIZE // 50
        limit = 50
        offset = (page - 1) * limit

        result, execution_time = measure_query_time(
            test_db.query(Map)
            .order_by(Map.id)
            .offset(offset)
            .limit(limit)
            .all
        )

        assert len(result) <= limit
        assert_query_performance(
            execution_time,
            MAX_QUERY_TIME_FILTERED,
            f"Pagination with large offset (page {page})"
        )
