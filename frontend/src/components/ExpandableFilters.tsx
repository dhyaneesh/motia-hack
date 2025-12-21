'use client';
import {
  Box,
  Button,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverBody,
  VStack,
  HStack,
  Text,
  Heading,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  Select,
  Checkbox
} from '@chakra-ui/react';
import { useState, useEffect, useMemo } from 'react';
import { useGraph } from '@/contexts/GraphContext';
import { useMode } from '@/contexts/ModeContext';

interface FilterState {
  minPrice: number;
  maxPrice: number;
  minRating: number;
  brand: string;
  availableOnly: boolean;
  sortBy: 'price-low' | 'price-high' | 'rating' | 'relevance';
}

export function ExpandableFilters() {
  const { graph } = useGraph();
  const { currentMode } = useMode();
  const [isOpen, setIsOpen] = useState(false);
  const [filters, setFilters] = useState<FilterState>({
    minPrice: 0,
    maxPrice: 1000,
    minRating: 0,
    brand: 'all',
    availableOnly: false,
    sortBy: 'relevance'
  });
  
  // Calculate price range from products (safe even if graph is null)
  const priceRange = useMemo(() => {
    if (!graph?.nodes) return { min: 0, max: 1000 };
    return graph.nodes.reduce((acc, node) => {
      const price = node.data?.price;
      if (price) {
        acc.min = Math.min(acc.min, price);
        acc.max = Math.max(acc.max, price);
      }
      return acc;
    }, { min: 0, max: 1000 });
  }, [graph?.nodes]);
  
  useEffect(() => {
    if (graph && priceRange.max > filters.maxPrice) {
      setFilters(prev => ({ ...prev, maxPrice: priceRange.max }));
    }
  }, [priceRange.max, graph]);
  
  // Only show in shopping mode when graph has nodes
  if (currentMode !== 'shopping' || !graph || graph.nodes.length === 0) {
    return null;
  }
  
  const handleFilterChange = (key: keyof FilterState, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };
  
  const applyFilters = () => {
    // Filter logic will be implemented in KnowledgeGraph component
    console.log('Applying filters:', filters);
    setIsOpen(false);
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
    <Box position="absolute" top={4} right={4} zIndex={10}>
      <Popover isOpen={isOpen} onOpen={() => setIsOpen(true)} onClose={() => setIsOpen(false)} placement="bottom-end">
        <PopoverTrigger>
          <Button size="sm" colorScheme="blue">
            Filter & Sort
          </Button>
        </PopoverTrigger>
        <PopoverContent w="300px" maxH="600px" overflowY="auto">
          <PopoverBody>
            <VStack align="stretch" spacing={4}>
              <Heading size="sm">Filters & Sort</Heading>
              
              {/* Price Range */}
              <Box>
                <Text fontSize="sm" fontWeight="medium" mb={2}>
                  Price: ${filters.minPrice.toFixed(0)} - ${filters.maxPrice.toFixed(0)}
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
                  Min Rating: {filters.minRating.toFixed(1)} ⭐
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
                <Text fontSize="sm" fontWeight="medium" mb={2}>Brand</Text>
                <Select
                  value={filters.brand}
                  onChange={(e) => handleFilterChange('brand', e.target.value)}
                  size="sm"
                >
                  <option value="all">All Brands</option>
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
                <Text fontSize="sm" fontWeight="medium" mb={2}>Sort By</Text>
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
          </PopoverBody>
        </PopoverContent>
      </Popover>
    </Box>
  );
}
