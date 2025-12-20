'use client';
import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Box, Text, Badge, Image, HStack, VStack, Link } from '@chakra-ui/react';
import { StarIcon } from '@chakra-ui/icons';

interface ProductNodeData {
  name: string;
  description: string;
  nodeType: string;
  clusterId: string;
  imageUrl?: string;
  price?: number;
  rating?: number;
  retailer?: string;
  url?: string;
  reviewSummary?: string;
  references: any[];
}

export const ProductNode = memo(({ data, selected }: NodeProps<ProductNodeData>) => {
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
            boxSize={3}
          />
        ))}
        <Text fontSize="xs" color="gray.600">
          {rating.toFixed(1)}
        </Text>
      </HStack>
    );
  };

  return (
    <Box
      w="200px"
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
      
      {/* Product Image */}
      {data.imageUrl && (
        <Image
          src={data.imageUrl}
          alt={data.name}
          w="100%"
          h="120px"
          objectFit="cover"
          borderTopRadius="lg"
        />
      )}
      
      <VStack align="stretch" p={2} spacing={1}>
        {/* Product Name */}
        <Text fontWeight="bold" fontSize="sm" noOfLines={2}>
          {data.name}
        </Text>
        
        {/* Price */}
        <Text fontSize="md" fontWeight="semibold" color="blue.600">
          {formatPrice(data.price)}
        </Text>
        
        {/* Rating */}
        {data.rating && renderStars(data.rating)}
        
        {/* Retailer */}
        {data.retailer && (
          <Text fontSize="xs" color="gray.500">
            {data.retailer}
          </Text>
        )}
        
        {/* Source Link */}
        {data.url && (
          <Link
            href={data.url}
            isExternal
            fontSize="xs"
            color="blue.500"
            onClick={(e) => e.stopPropagation()}
          >
            View Source →
          </Link>
        )}
      </VStack>
      
      <Handle type="source" position={Position.Bottom} />
    </Box>
  );
});

ProductNode.displayName = 'ProductNode';
