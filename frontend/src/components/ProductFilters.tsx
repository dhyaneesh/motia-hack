'use client';
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Select,
  Checkbox,
  Button
} from '@chakra-ui/react';
import { useState, useEffect } from 'react';
import { useGraph } from '@/contexts/GraphContext';

interface FilterState {
  minPrice: number;
  maxPrice: number;
  minRating: number;
  brand: string;
  availableOnly: boolean;
  sortBy: 'price-low' | 'price-high' | 'rating' | 'relevance';
}

export function ProductFilters() {
  const { graph } = useGraph();
  const [filters, setFilters] = useState<FilterState>({
    minPrice: 0,
    maxPrice: 1000,
    minRating: 0,
    brand: 'all',
    availableOnly: false,
    sortBy: 'relevance'
  });
  
  // Calculate price range from products
  const priceRange = graph?.nodes?.reduce((acc, node) => {
    const price = node.data?.price;
    if (price) {
      acc.min = Math.min(acc.min, price);
      acc.max = Math.max(acc.max, price);
    }
    return acc;
  }, { min: 0, max: 1000 }) || { min: 0, max: 1000 };
  
  useEffect(() => {
    // Update max price when graph changes
    if (priceRange.max > filters.maxPrice) {
      setFilters(prev => ({ ...prev, maxPrice: priceRange.max }));
    }
  }, [priceRange.max]);
  
  const handleFilterChange = (key: keyof FilterState, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };
  
  const applyFilters = () => {
    // Filter logic will be implemented in KnowledgeGraph component
    // This component just manages filter state
    console.log('Applying filters:', filters);
  };
  
  const resetFilters = () => {
    setFilters({
      minPrice: 0,
      maxPrice: priceRange.max,
      minRating: 0,
      brand: 'all',
      availableOnly: false,
      sortBy: 'relevance'
    });
  };
  
  return (
    <Box
      w="250px"
      h="100vh"
      overflowY="auto"
      p={4}
      bg="white"
      borderRight="1px"
      borderColor="gray.200"
    >
      <Heading size="sm" mb={4}>Filters & Sort</Heading>
      
      <VStack align="stretch" spacing={6}>
        {/* Price Range */}
        <Box>
          <Text fontSize="sm" fontWeight="medium" mb={2}>
            Price Range: ${filters.minPrice.toFixed(0)} - ${filters.maxPrice.toFixed(0)}
          </Text>
          <VStack spacing={2}>
            <Slider
              value={filters.minPrice}
              min={0}
              max={priceRange.max}
              onChange={(val) => handleFilterChange('minPrice', val)}
            >
              <SliderTrack>
                <SliderFilledTrack />
              </SliderTrack>
              <SliderThumb />
            </Slider>
            <Slider
              value={filters.maxPrice}
              min={0}
              max={priceRange.max}
              onChange={(val) => handleFilterChange('maxPrice', val)}
            >
              <SliderTrack>
                <SliderFilledTrack />
              </SliderTrack>
              <SliderThumb />
            </Slider>
          </VStack>
        </Box>
        
        {/* Rating */}
        <Box>
          <Text fontSize="sm" fontWeight="medium" mb={2}>
            Minimum Rating: {filters.minRating.toFixed(1)} ⭐
          </Text>
          <Slider
            value={filters.minRating}
            min={0}
            max={5}
            step={0.5}
            onChange={(val) => handleFilterChange('minRating', val)}
          >
            <SliderTrack>
              <SliderFilledTrack />
            </SliderTrack>
            <SliderThumb />
          </Slider>
        </Box>
        
        {/* Brand */}
        <Box>
          <Text fontSize="sm" fontWeight="medium" mb={2}>
            Brand
          </Text>
          <Select
            value={filters.brand}
            onChange={(e) => handleFilterChange('brand', e.target.value)}
            size="sm"
          >
            <option value="all">All Brands</option>
            {/* Brand options would be populated from products */}
          </Select>
        </Box>
        
        {/* Availability */}
        <Checkbox
          isChecked={filters.availableOnly}
          onChange={(e) => handleFilterChange('availableOnly', e.target.checked)}
        >
          Available Only
        </Checkbox>
        
        {/* Sort */}
        <Box>
          <Text fontSize="sm" fontWeight="medium" mb={2}>
            Sort By
          </Text>
          <Select
            value={filters.sortBy}
            onChange={(e) => handleFilterChange('sortBy', e.target.value)}
            size="sm"
          >
            <option value="relevance">Relevance</option>
            <option value="price-low">Price: Low to High</option>
            <option value="price-high">Price: High to Low</option>
            <option value="rating">Rating</option>
          </Select>
        </Box>
        
        {/* Action Buttons */}
        <HStack spacing={2}>
          <Button size="sm" colorScheme="blue" onClick={applyFilters} flex={1}>
            Apply
          </Button>
          <Button size="sm" variant="outline" onClick={resetFilters} flex={1}>
            Reset
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
}
