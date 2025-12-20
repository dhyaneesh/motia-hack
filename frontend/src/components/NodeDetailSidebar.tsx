'use client';
import {
  Box,
  VStack,
  HStack,
  Text,
  Heading,
  Badge,
  Link,
  Button,
  IconButton,
  Divider,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Spinner,
  useToast,
  Image
} from '@chakra-ui/react';
import { CloseIcon, ExternalLinkIcon, AddIcon, StarIcon } from '@chakra-ui/icons';
import { useGraph } from '@/contexts/GraphContext';
import { useMode } from '@/contexts/ModeContext';
import { api } from '@/services/api';
import { useState } from 'react';

export function NodeDetailSidebar() {
  const { selectedNode, selectNode, addToGraph } = useGraph();
  const { currentMode } = useMode();
  const [isExpanding, setIsExpanding] = useState(false);
  const toast = useToast();
  
  if (!selectedNode) return null;
  
  const handleClose = () => selectNode(null);
  
  // Check if this is a product node
  const node = selectedNode as any;
  const isProduct = currentMode === 'shopping' || node.imageUrl || node.price !== undefined;
  
  const formatPrice = (price: number | undefined) => {
    if (!price) return 'N/A';
    return `$${price.toFixed(2)}`;
  };
  
  const renderStars = (rating: number | undefined) => {
    if (!rating) return null;
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    
    return (
      <HStack spacing={0.5}>
        {[...Array(5)].map((_, i) => (
          <StarIcon
            key={i}
            color={i < fullStars ? 'yellow.400' : i === fullStars && hasHalfStar ? 'yellow.300' : 'gray.300'}
            boxSize={4}
          />
        ))}
        <Text fontSize="sm" color="gray.600">
          {rating.toFixed(1)}
        </Text>
      </HStack>
    );
  };
  
  const handleExpand = async () => {
    setIsExpanding(true);
    try {
      const { newNodes, newEdges } = await api.expandNode(selectedNode.id);
      addToGraph(newNodes, newEdges);
      toast({
        title: 'Success',
        description: `Added ${newNodes.length} new nodes`,
        status: 'success',
        duration: 3000,
        isClosable: true
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to expand node',
        status: 'error',
        duration: 5000,
        isClosable: true
      });
    } finally {
      setIsExpanding(false);
    }
  };
  
  return (
    <Box h="100vh" overflowY="auto" p={4} bg="white">
      {/* Header */}
      <HStack justify="space-between" mb={4}>
        <Heading size="md" noOfLines={2}>{selectedNode.name}</Heading>
        <IconButton
          aria-label="Close sidebar"
          icon={<CloseIcon />}
          size="sm"
          onClick={handleClose}
        />
      </HStack>
      
      {/* Product Image */}
      {isProduct && node.imageUrl && (
        <Image
          src={node.imageUrl}
          alt={selectedNode.name}
          w="100%"
          maxH="300px"
          objectFit="contain"
          borderRadius="lg"
          mb={4}
        />
      )}
      
      {/* Price and Rating (for products) */}
      {isProduct && (
        <HStack justify="space-between" mb={4}>
          <Text fontSize="2xl" fontWeight="bold" color="blue.600">
            {formatPrice(node.price)}
          </Text>
          {renderStars(node.rating)}
        </HStack>
      )}
      
      {/* Type Badge */}
      <Badge colorScheme={isProduct ? 'blue' : 'green'} mb={4}>
        {isProduct ? 'Product' : selectedNode.type}
      </Badge>
      
      {/* Retailer (for products) */}
      {isProduct && node.retailer && (
        <Badge colorScheme="blue" mb={4} mr={2}>
          {node.retailer}
        </Badge>
      )}
      
      {/* Description */}
      <Text fontSize="sm" color="gray.700" mb={4}>
        {selectedNode.description}
      </Text>
      
      <Divider my={4} />
      
      {/* Specifications (for products) */}
      {isProduct && node.specs && Object.keys(node.specs).length > 0 && (
        <>
          <Heading size="sm" mb={3}>Specifications</Heading>
          <VStack align="stretch" spacing={2} mb={4}>
            {Object.entries(node.specs).map(([key, value]) => (
              <HStack key={key} justify="space-between">
                <Text fontSize="sm" fontWeight="medium" color="gray.600">
                  {key}:
                </Text>
                <Text fontSize="sm" color="gray.800">
                  {String(value)}
                </Text>
              </HStack>
            ))}
          </VStack>
          <Divider my={4} />
        </>
      )}
      
      {/* Review Summary (for products) */}
      {isProduct && node.reviewSummary && (
        <>
          <Heading size="sm" mb={3}>Review Summary</Heading>
          <Box
            p={3}
            bg="gray.50"
            borderRadius="md"
            mb={4}
          >
            <Text fontSize="sm" color="gray.700" whiteSpace="pre-wrap">
              {node.reviewSummary}
            </Text>
          </Box>
          <Divider my={4} />
        </>
      )}
      
      {/* Study Mode: Level and Prerequisites */}
      {currentMode === 'study' && (
        <>
          {node.level && (
            <Box mb={4}>
              <Heading size="sm" mb={2}>Level</Heading>
              <Badge colorScheme={node.level === 1 ? 'green' : node.level === 2 ? 'yellow' : 'red'}>
                {node.level === 1 ? 'Beginner' : node.level === 2 ? 'Intermediate' : 'Advanced'}
              </Badge>
            </Box>
          )}
          {node.prerequisites && node.prerequisites.length > 0 && (
            <Box mb={4}>
              <Heading size="sm" mb={2}>Prerequisites</Heading>
              <VStack align="stretch" spacing={1}>
                {node.prerequisites.map((prereq: string, idx: number) => (
                  <Text key={idx} fontSize="sm" color="gray.600" pl={2}>
                    • {prereq}
                  </Text>
                ))}
              </VStack>
            </Box>
          )}
          <Divider my={4} />
        </>
      )}
      
      {/* References Section */}
      <Heading size="sm" mb={3}>References ({selectedNode.references.length})</Heading>
      
      {selectedNode.references.length > 0 ? (
        <Accordion allowMultiple>
          {selectedNode.references.map((ref, index) => (
            <AccordionItem key={ref.id || index}>
              <AccordionButton>
                <Box flex="1" textAlign="left">
                  <Text fontSize="sm" fontWeight="medium" noOfLines={2}>
                    {ref.title}
                  </Text>
                  <Text fontSize="xs" color="gray.500">
                    {ref.publishedDate ? new Date(ref.publishedDate).toLocaleDateString() : 'No date'}
                  </Text>
                </Box>
                <AccordionIcon />
              </AccordionButton>
              <AccordionPanel pb={4}>
                {/* Article Excerpt */}
                <Text fontSize="sm" color="gray.600" mb={3} noOfLines={6}>
                  {ref.text?.substring(0, 500)}...
                </Text>
                
                {/* Source Link */}
                <Link href={ref.url} isExternal color="blue.500" fontSize="sm">
                  View Source <ExternalLinkIcon mx="2px" />
                </Link>
                
                {ref.author && (
                  <Text fontSize="xs" color="gray.500" mt={1}>
                    By {ref.author}
                  </Text>
                )}
              </AccordionPanel>
            </AccordionItem>
          ))}
        </Accordion>
      ) : (
        <Text fontSize="sm" color="gray.500" fontStyle="italic">
          No references available
        </Text>
      )}
      
      <Divider my={4} />
      
      {/* Related Nodes */}
      <Heading size="sm" mb={3}>
        {isProduct ? 'Related Products' : 'Related Concepts'}
      </Heading>
      {selectedNode.relatedNodes.length > 0 ? (
        <VStack align="stretch" spacing={2}>
          {selectedNode.relatedNodes.map((related) => (
            <Button
              key={related.id}
              size="sm"
              variant="ghost"
              justifyContent="flex-start"
              onClick={async () => {
                try {
                  const details = await api.getNodeDetails(related.id);
                  selectNode(details);
                } catch (error) {
                  toast({
                    title: 'Error',
                    description: 'Failed to load node details',
                    status: 'error',
                    duration: 3000,
                    isClosable: true
                  });
                }
              }}
            >
              {related.name}
            </Button>
          ))}
        </VStack>
      ) : (
        <Text fontSize="sm" color="gray.500" fontStyle="italic">
          {isProduct ? 'No related products' : 'No related concepts'}
        </Text>
      )}
      
      {/* Expand Button (only for default/study modes, not shopping) */}
      {currentMode !== 'shopping' && (
        <>
          <Divider my={4} />
          <Button
            leftIcon={isExpanding ? <Spinner size="sm" /> : <AddIcon />}
            colorScheme="blue"
            w="full"
            onClick={handleExpand}
            isDisabled={isExpanding}
          >
            {isExpanding ? 'Expanding...' : 'Expand & Find More'}
          </Button>
        </>
      )}
    </Box>
  );
}

