'use client';
import { memo, useState } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Box, Text, Badge, VStack, HStack, Link, Collapse, IconButton } from '@chakra-ui/react';
import { ChevronDownIcon, ChevronUpIcon, ExternalLinkIcon } from '@chakra-ui/icons';

interface ConceptCardData {
  name: string;
  description: string;
  nodeType: string;
  clusterId: string;
  level?: number; // 1=Beginner, 2=Intermediate, 3=Advanced
  prerequisites?: string[];
  learningPathPosition?: number;
  references: any[];
}

const levelLabels = {
  1: { label: 'Beginner', color: 'green' },
  2: { label: 'Intermediate', color: 'yellow' },
  3: { label: 'Advanced', color: 'red' }
};

export const ConceptCard = memo(({ data, selected }: NodeProps<ConceptCardData>) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const level = data.level || 2;
  const levelInfo = levelLabels[level as keyof typeof levelLabels] || levelLabels[2];

  return (
    <Box
      w="220px"
      bg="white"
      border="2px"
      borderColor={selected ? 'blue.500' : 'gray.300'}
      borderRadius="lg"
      boxShadow={selected ? 'lg' : 'md'}
      cursor="pointer"
      _hover={{ borderColor: 'blue.400', boxShadow: 'lg' }}
      transition="all 0.2s"
      overflow="hidden"
    >
      <Handle type="target" position={Position.Top} />
      
      <VStack align="stretch" p={3} spacing={2}>
        {/* Header with level badge */}
        <HStack justify="space-between" align="start">
          <Badge colorScheme={levelInfo.color} fontSize="xs">
            {levelInfo.label}
          </Badge>
          <IconButton
            aria-label={isExpanded ? 'Collapse' : 'Expand'}
            icon={isExpanded ? <ChevronUpIcon /> : <ChevronDownIcon />}
            size="xs"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
          />
        </HStack>
        
        {/* Concept Name */}
        <Text fontWeight="bold" fontSize="sm" noOfLines={2}>
          {data.name}
        </Text>
        
        {/* Brief Description (always visible) */}
        <Text fontSize="xs" color="gray.600" noOfLines={2}>
          {data.description}
        </Text>
        
        {/* Expanded Content */}
        <Collapse in={isExpanded} animateOpacity>
          <VStack align="stretch" spacing={2} mt={2} pt={2} borderTop="1px" borderColor="gray.200">
            {/* Full Description */}
            <Text fontSize="xs" color="gray.700" whiteSpace="pre-wrap">
              {data.description}
            </Text>
            
            {/* Prerequisites */}
            {data.prerequisites && data.prerequisites.length > 0 && (
              <Box>
                <Text fontSize="xs" fontWeight="medium" color="gray.600" mb={1}>
                  Prerequisites:
                </Text>
                <VStack align="stretch" spacing={1}>
                  {data.prerequisites.map((prereq, idx) => (
                    <Text key={idx} fontSize="xs" color="gray.500" pl={2}>
                      • {prereq}
                    </Text>
                  ))}
                </VStack>
              </Box>
            )}
            
            {/* Source Links */}
            {data.references && data.references.length > 0 && (
              <Box>
                <Text fontSize="xs" fontWeight="medium" color="gray.600" mb={1}>
                  Sources:
                </Text>
                <VStack align="stretch" spacing={1}>
                  {data.references.slice(0, 2).map((ref, idx) => (
                    <Link
                      key={ref.id || idx}
                      href={ref.url}
                      isExternal
                      fontSize="xs"
                      color="blue.500"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {ref.title} <ExternalLinkIcon mx="2px" boxSize={2} />
                    </Link>
                  ))}
                </VStack>
              </Box>
            )}
          </VStack>
        </Collapse>
      </VStack>
      
      <Handle type="source" position={Position.Bottom} />
    </Box>
  );
});

ConceptCard.displayName = 'ConceptCard';
