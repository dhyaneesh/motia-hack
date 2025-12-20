import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Box, Text, Badge } from '@chakra-ui/react';
import { NodeData } from '@/types';

const nodeColors: Record<string, string> = {
  concept: 'blue.100',
  entity: 'green.100',
  event: 'orange.100',
  person: 'purple.100'
};

export const ConceptNode = memo(({ data, selected }: NodeProps<NodeData>) => {
  return (
    <Box
      px={4}
      py={3}
      bg={nodeColors[data.nodeType] || 'gray.100'}
      border="2px"
      borderColor={selected ? 'blue.500' : 'gray.300'}
      borderRadius="lg"
      boxShadow={selected ? 'lg' : 'md'}
      minW="150px"
      maxW="250px"
      cursor="pointer"
      _hover={{ borderColor: 'blue.400', boxShadow: 'lg' }}
      transition="all 0.2s"
    >
      <Handle type="target" position={Position.Top} />
      
      <Badge colorScheme={data.nodeType === 'concept' ? 'blue' : 'green'} mb={1}>
        {data.nodeType}
      </Badge>
      <Text fontWeight="bold" fontSize="sm" noOfLines={2}>
        {data.name}
      </Text>
      <Text fontSize="xs" color="gray.600" noOfLines={2} mt={1}>
        {data.description}
      </Text>
      
      <Handle type="source" position={Position.Bottom} />
    </Box>
  );
});

ConceptNode.displayName = 'ConceptNode';

