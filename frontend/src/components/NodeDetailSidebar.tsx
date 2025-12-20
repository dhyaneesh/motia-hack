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
  useToast
} from '@chakra-ui/react';
import { CloseIcon, ExternalLinkIcon, AddIcon } from '@chakra-ui/icons';
import { useGraph } from '@/contexts/GraphContext';
import { api } from '@/services/api';
import { useState } from 'react';

export function NodeDetailSidebar() {
  const { selectedNode, selectNode, addToGraph } = useGraph();
  const [isExpanding, setIsExpanding] = useState(false);
  const toast = useToast();
  
  if (!selectedNode) return null;
  
  const handleClose = () => selectNode(null);
  
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
      
      {/* Type Badge */}
      <Badge colorScheme="blue" mb={4}>{selectedNode.type}</Badge>
      
      {/* Description */}
      <Text fontSize="sm" color="gray.700" mb={4}>
        {selectedNode.description}
      </Text>
      
      <Divider my={4} />
      
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
      <Heading size="sm" mb={3}>Related Concepts</Heading>
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
          No related concepts
        </Text>
      )}
      
      <Divider my={4} />
      
      {/* Expand Button */}
      <Button
        leftIcon={isExpanding ? <Spinner size="sm" /> : <AddIcon />}
        colorScheme="blue"
        w="full"
        onClick={handleExpand}
        isDisabled={isExpanding}
      >
        {isExpanding ? 'Expanding...' : 'Expand & Find More'}
      </Button>
    </Box>
  );
}

