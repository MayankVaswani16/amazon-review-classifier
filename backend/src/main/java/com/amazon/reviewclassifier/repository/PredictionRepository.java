package com.amazon.reviewclassifier.repository;

import com.amazon.reviewclassifier.entity.Prediction;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PredictionRepository extends JpaRepository<Prediction, Long> {

    Page<Prediction> findAllByOrderByCreatedAtDesc(Pageable pageable);

    long countByLabel(String label);

    @Query("SELECT AVG(p.confidence) FROM Prediction p")
    Double findAverageConfidence();

    @Query(value = "SELECT noun AS word, COUNT(*) AS cnt FROM prediction_nouns GROUP BY noun ORDER BY cnt DESC LIMIT 10", nativeQuery = true)
    List<Object[]> findTopNouns();

    @Query(value = "SELECT adjective AS word, COUNT(*) AS cnt FROM prediction_adjectives GROUP BY adjective ORDER BY cnt DESC LIMIT 10", nativeQuery = true)
    List<Object[]> findTopAdjectives();

    @org.springframework.data.jpa.repository.Modifying
    @Query(value = "TRUNCATE TABLE predictions CASCADE", nativeQuery = true)
    void truncateAll();
}

