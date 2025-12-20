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
  Image,
  useToast
} from '@chakra-ui/react';
import { CloseIcon, ExternalLinkIcon, StarIcon } from '@chakra-ui/icons';
import { useGraph } from '@/contexts/GraphContext';
import { api } from '@/services/api';

interface ProductDetails {
  id: string;
  name: string;
  description: string;
  imageUrl?: string;
  price?: number;
  rating?: number;
  retailer?: string;
  url?: string;
  specs?: Record<string, any>;
  reviewSummary?: string;
  references: any[];
}

export function ProductDetailSidebar() {
  const { selectedNode, selectNode } = useGraph();
  const toast = useToast();
  
  if (!selectedNode) return null;
  
  // Check if this is a product node
  const isProduct = selectedNode.type === 'product' || (selectedNode as any).imageUrl || (selectedNode as any).price !== undefined;
  
  if (!isProduct) {
    // Not a product, don't render this sidebar
    return null;
  }
  
  // Cast to ProductDetails if it's a product
  const product = selectedNode as any as ProductDetails;
  
  const handleClose = () => selectNode(null);
  
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
  
  return (
    <Box h="100vh" overflowY="auto" p={4} bg="white">
      {/* Header */}
      <HStack justify="space-between" mb={4}>
        <Heading size="md" noOfLines={2}>{product.name}</Heading>
        <IconButton
          aria-label="Close sidebar"
          icon={<CloseIcon />}
          size="sm"
          onClick={handleClose}
        />
      </HStack>
      
      {/* Product Image */}
      {product.imageUrl && (
        <Image
          src={product.imageUrl}
          alt={product.name}
          w="100%"
          maxH="300px"
          objectFit="contain"
          borderRadius="lg"
          mb={4}
        />
      )}
      
      {/* Price and Rating */}
      <HStack justify="space-between" mb={4}>
        <Text fontSize="2xl" fontWeight="bold" color="blue.600">
          {formatPrice(product.price)}
        </Text>
        {product.rating && renderStars(product.rating)}
      </HStack>
      
      {/* Retailer */}
      {product.retailer && (
        <Badge colorScheme="blue" mb={4}>
          {product.retailer}
        </Badge>
      )}
      
      {/* Description */}
      <Text fontSize="sm" color="gray.700" mb={4}>
        {product.description}
      </Text>
      
      <Divider my={4} />
      
      {/* Specifications */}
      {product.specs && Object.keys(product.specs).length > 0 && (
        <>
          <Heading size="sm" mb={3}>Specifications</Heading>
          <VStack align="stretch" spacing={2} mb={4}>
            {Object.entries(product.specs).map(([key, value]) => (
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
      
      {/* Review Summary */}
      {product.reviewSummary && (
        <>
          <Heading size="sm" mb={3}>Review Summary</Heading>
          <Box
            p={3}
            bg="gray.50"
            borderRadius="md"
            mb={4}
          >
            <Text fontSize="sm" color="gray.700" whiteSpace="pre-wrap">
              {product.reviewSummary}
            </Text>
          </Box>
          <Divider my={4} />
        </>
      )}
      
      {/* Source Links */}
      <Heading size="sm" mb={3}>Source Links</Heading>
      {product.url ? (
        <VStack align="stretch" spacing={2}>
          <Link
            href={product.url}
            isExternal
            color="blue.500"
            fontSize="sm"
            fontWeight="medium"
          >
            View Product <ExternalLinkIcon mx="2px" />
          </Link>
          {product.references && product.references.length > 0 && (
            <>
              {product.references.map((ref, index) => (
                <Link
                  key={ref.id || index}
                  href={ref.url}
                  isExternal
                  color="blue.500"
                  fontSize="sm"
                >
                  {ref.title} <ExternalLinkIcon mx="2px" />
                </Link>
              ))}
            </>
          )}
        </VStack>
      ) : (
        <Text fontSize="sm" color="gray.500" fontStyle="italic">
          No source links available
        </Text>
      )}
    </Box>
  );
}
